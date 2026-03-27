# ISP Pipeline Design

**Sections 1-6 relate to Part 1, whilst sections 7-9 relate to Part 2**

## 1. Overview

- **What this pipeline does**: Generate synthetic single-cell expression data, apply perturbations (KO/AC/OE), run a mock model to produce embeddings, and compute distances versus baseline.

- **What is mocked**: Model inference is mocked (`run_model`) and returns random embeddings; no real foundation model integration. Data is saved to an ephemeral database that is destroyed when the container is shutdown.

- **What scale this demo uses**: The data scale can be varied using the fixed parameters in the `consts.py` file, as well as by the parameters submitted to the `api/rest/demo` endpoint. It currently does not utilise any parallelism, but scope is present for concurrency gains through the `BATCH_SIZE` parameter. This also effectively controls the tradeoff against max memory useage and concurrency.

## 2. Input Design

- AnnData shape used in demo: Configurable synthetic matrix (e.g. API-driven `obs`, `vars`, `perts` values).

- `obs` fields (cell metadata): `cell_type`, `donor`, `batch`. (Automatically generated).

- `var` fields (gene metadata): `gene_symbol`, `chromosome`. (Automatically generated).

- Perturbation spec format (`gene`, `type`): `PertSpec { gene, ptype }` with `ptype in {KO, AC, OE}`.

- How perturbations are applied without copying full matrices: The pipeline mutates only the target gene column in-place on a single shared AnnData, runs inference, and restores the original column in a try/finally block, so each perturbation is processed sequentially with low memory overhead and no full-matrix copies.

## 3. Output Design

- Embedding output shape (expected `(n_cells, 512)`): Current code stores per-cell embeddings but configured embedding length set to 512.

- Where embeddings are stored: In relational DB table `Embedding` with fields `(cell (foreign key), perturbation_gene (foreign key), perturbation_type, value, dist)`.

- How results are organized for:
  - UI browsing: GraphQL types expose cells/genes/expressions/embeddings with filters and ordering, accessible via GraphiQL web-based GUI.
  - Downstream analysis: Embeddings and distances are queryable from DB via GraphQL requests, though storage format is not yet optimized for high-scale analytics.

## 4. Memory & Trade-offs

- Peak memory during:
  1. Baseline embedding run: one base AnnData matrix plus one baseline embedding array (n_cells x embedding_dim).
  2. Perturbation run: one temporary backup of a single target gene column, the same shared AnnData mutated in-place, and one perturbed embedding array.
  3. Persistence phase: in-memory Embedding ORM objects accumulated per batch_size before bulk insert.

- Memory strategy: perturbations are applied to one gene column at a time on a shared matrix and then restored in a try/finally block, which avoids creating full AnnData copies per condition.

- Main trade-offs made:
  - Memory vs speed: in-place mutation greatly reduces RAM use compared with per-perturbation matrix copies, but adds per-iteration restore overhead.
  - The model needs to be run sequentially (not concurrently / in-parallel) since only one perturbation exists at a time.
  - DB throughput vs RAM: batching writes with bulk_create improves insert performance but increases temporary memory usage as batch_size grows.

- Practical implication: peak matrix memory is close to “base matrix + one column backup,” while most tunable memory pressure comes from embedding buffers and DB write batch size.

## 5. Pipeline Implementation

- Data generation step: generate_random_data builds synthetic sparse expression data (AnnData) with realistic obs (cell_type, donor, batch) and var (gene_symbol, chromosome) metadata, plus perturbation specs.

- Baseline step: the pipeline runs run_model(adata) once on the unperturbed matrix and stores baseline embeddings per cell.

- Perturbation execution step: perturbations are processed sequentially in batches; for each spec, the target gene column is backed up, mutated in-place (KO/AC/OE), yielded for inference, and restored in a try/finally block to guarantee matrix integrity.

- Comparison step: for each perturbation condition, cosine distance is computed cell-wise between perturbed and baseline embeddings.

- Persistence step: an SQLite db is currently used via the Django ORM. Genes/cells are inserted, expression rows are stored, and perturbation embeddings with distance scores are accumulated and written via bulk_create once per batch.

## 6. Queries

- How to avoid loading all embeddings (or other data) into memory:
  - paginate DB queries if suitable for the task, or stream data in chunks to the user.
  - construct queries with filters lazily and evaluate all at once only when necessary.

- Django ORM takes care of a lot of memory and DB access optimisations, but further improvements could be made using manually written SQL queries in certain complex cases.

- GraphQL allows users to specify exactly what information they want to avoid sending over excessive data.
  - An example query to retrieve embedding shifts (dist) where `Gene_X` has been knocked out (`KO`) for donor `Donor_3`'s T-cells (`T`)':

    ```gql
    query ExampleQuery {
      embeddings(filters: {
          cell: {donor: {exact: "Donor_3"}, type: {exact: "T"}},
          perturbationGene: {label: {exact: "Gene_X"}},
          perturbationType: {exact: "KO"},
      }) {
        id
        dist
        cell {
          label
          id
        }
      }
    }
    ```

## 7. API Contract

### Create Job
- `POST /api/rest/jobs`
- Request: dataset reference + perturbation list + optional filters.
- Response: `job_id`, initial status (`queued`).

### Check Status
- `GET /api/rest/jobs/{job_id}`
- Response: `status`, `progress`, timestamps, error (if failed).

### Fetch Results
- `GET /api/rest/jobs/{job_id}/results` OR GraphQL interface `POST /api/gql`
- Filters: gene, perturbation type, donor, cell type, cursor/limit.
- Response: paginated (if suitable) per-cell embeddings and distance metrics. For GraphQL interface, the endpoint consumer can request the exact desired data from the graph structure.

## 8. Scalability Plan

- Queue + worker model: API enqueues perturbation jobs; stateless workers (e.g. AWS Lambdas) process perturbation batches and write outputs. This will scale up and down easily for variable workloads, ensuring compute power is used efficiently.

- Storage design for large jobs: metadata in relational DB; large embedding matrices in columnar/object storage with references in DB. Regionally separated backups for disaster recovery.

- Expected bottlenecks: model inference throughput, DB write amplification, and retrieval latency for large embedding payloads.
  - Mitigations: worker autoscaling, batching/chunking, partitioned storage, result caching, async query endpoints.

## 9. Deployment Plan

- Containerization approach: separate containers for API, workers, and DB adapter services.

- Runtime/orchestrator (k8s/ECS/etc):
  - For smaller scales, a Scheduler VM that can request serverless Lambda instances, along with a separate VM for API handling may be sufficient.
  - For larger scales, a Kubernetes with separate node pools for CPU API pods and GPU worker pods would be more reliable and worth the complexity tradeoff.

- GPU worker allocation approach: queue-based scheduling with resource requests/limits and dedicated GPU worker deployment.

- Basic observability (logs/metrics): structured logs, queue depth metrics, worker throughput, error rates, latency dashboards.
