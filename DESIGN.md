# ISP Pipeline Design

**Sections 1-6 relate primarily to Part 1, whilst Sections 7-9 relate primarily to Part 2.**

## 1. Overview

- **What this pipeline does**: Generate synthetic single-cell expression data, apply perturbations (`KO`/`AC`/`OE`), run a mock model to produce embeddings, and compute distances versus baseline.

- **What is mocked**: Model inference is mocked (`run_model`) and returns random embeddings; no real foundation model integration. Data is saved to an ephemeral database that is destroyed when the container is shut down.

- **What scale this demo uses**: Data scale can be varied using fixed parameters in `src/logic/consts.py` and request parameters submitted to `POST /api/rest/demo`. Perturbations are processed sequentially because each run mutates a shared `AnnData` in-place and then restores it. This preserves state isolation and keeps peak memory low.

- **How to adapt for larger scales**: For larger workloads, the same logic can be parallelised by partitioning perturbation conditions across isolated workers. Each worker handles a separate data shard and writes embeddings/distances asynchronously to shared storage.

## 2. Input Design

- **`AnnData` shape used in demo**: Configurable synthetic matrix (e.g. API-driven `obs`, `vars`, `perts` values).

- **`obs` fields (cell metadata)**: `cell_type`, `donor`, `batch`. (Automatically generated).

- **`var` fields (gene metadata)**: `gene_symbol`, `chromosome`. (Automatically generated).

- **Perturbation spec format (`gene`, `type`)**: `PertSpec { gene, ptype }` with `ptype in {KO, AC, OE}`.

- **How perturbations are applied without copying full matrices**: The pipeline mutates only the target gene column in-place on a shared `AnnData`, runs inference, and restores the original column in a `try/finally` block. This avoids full-matrix copies and keeps memory overhead low.

## 3. Output Design

- **Embedding output shape (expected `(n_cells, 512)`)**: Current code stores per-cell embeddings, with embedding length set to `512`.

- **Where embeddings are stored**: In the relational DB table `Embedding` with fields `(cell [foreign key], perturbation_gene [foreign key], perturbation_type, value, dist)`.

- **How results are organised for**:
  - *UI browsing*: GraphQL types expose cells/genes/expressions/embeddings with filters and ordering, accessible via GraphiQL web-based GUI.
  - *Downstream analysis*: Embeddings and distances are queryable from the DB via GraphQL requests, though the storage format is not yet optimised for high-scale analytics.

- **Storage scalability caveat**: Storing vectors in `Embedding.value` as `JSONField` is a demo-friendly choice, but it is not optimal for large-scale analytics (e.g. clustering or differential analysis). At production scale, embeddings would be better placed in columnar/object or vector-optimised storage, with indexed references in the relational DB.

## 4. Memory & Trade-offs

- **Peak memory during**:
  1. Baseline embedding run: one base `AnnData` matrix plus one baseline embedding array (`n_cells x embedding_dim`).
  2. Perturbation run: one temporary backup of a single target gene column, the same shared `AnnData` mutated in-place, and one perturbed embedding array.
  3. Persistence phase: in-memory `Embedding` ORM objects accumulated per `batch_size` before bulk insert.

- **Memory strategy**: Perturbations are applied to one gene column at a time on a shared matrix and then restored in a `try/finally` block, which avoids creating full `AnnData` copies per condition.

- **Main trade-offs made**:
  - *Memory vs speed*: in-place mutation greatly reduces RAM use compared with per-perturbation matrix copies, but adds per-iteration restore overhead.
  - *Execution model constraint*: The model needs to be run sequentially (not concurrently / in parallel) since only one perturbation exists at a time.
  - *DB throughput vs RAM*: batching writes with `bulk_create` improves insert performance but increases temporary memory usage as `batch_size` grows.
  - *Semantic completeness vs storage cost*: The persistence logic writes explicit zero-valued `Expression` rows so that "measured zero" is distinguishable from "not measured" for each cell-gene pair. This improves interpretability and query semantics, but increases write volume and storage footprint at larger scales.
  - *Potential optimisation path*: At larger scales, this can be replaced with sparse-only storage plus an explicit measurement-status flag (or equivalent metadata) to preserve semantic clarity with lower storage overhead.

- **Practical implication**: Peak matrix memory is close to "base matrix + one column backup". Most tunable memory pressure comes from embedding buffers and DB write batch size.

## 5. Pipeline Implementation

- **Data generation step**: `generate_random_data` builds synthetic sparse expression data (`AnnData`) with realistic `obs` (`cell_type`, `donor`, `batch`) and `var` (`gene_symbol`, `chromosome`) metadata, plus perturbation specs.

- **Baseline step**: The pipeline runs `run_model(adata)` once on the unperturbed matrix and stores baseline embeddings per cell.

- **Perturbation execution step**: Perturbations are processed sequentially in batches. For each spec, the target gene column is backed up, mutated in-place (`KO`/`AC`/`OE`), yielded for inference, and restored in a `try/finally` block.

- **Comparison step**: For each perturbation condition, cosine distance is computed cell-wise between perturbed and baseline embeddings.

- **Persistence step**: An `SQLite` DB is used via the Django ORM. `Gene`/`Cell` rows are inserted, `Expression` rows are stored, and perturbation embeddings with distance scores are accumulated and written via `bulk_create` once per batch.

## 6. Queries

- **How to avoid loading all embeddings (or other data) into memory**:
  - Paginate DB queries if suitable for the task, or stream data in chunks to the user.
  - Construct queries with filters lazily and evaluate all at once only when necessary.

- **ORM optimisation notes**: Django ORM handles many memory and DB access optimisations. Further improvements could use manually written SQL for specific complex cases.

- **GraphQL data minimisation**: GraphQL allows users to specify exactly what information they want to avoid sending over excessive data.
  - *Example query* to retrieve embedding shifts (`dist`) where `Gene_X` has been knocked out (`KO`) for donor `Donor_3`'s T-cells (`T`):

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

- **Implementation status**: The `/jobs` endpoints below are proposed architecture for production scale and are not implemented in the current codebase. The current implementation exposes `POST /api/rest/demo`, `GET /api/rest/healthcheck`, and GraphQL queries via `POST /api/gql`.

### Create Job
- **Endpoint**: `POST /api/rest/jobs`
- **Request**: Dataset reference + perturbation list + optional filters.
- **Response**: `job_id`, initial status (`queued`).

### Check Status
- **Endpoint**: `GET /api/rest/jobs/{job_id}`
- **Response**: `status`, `progress`, timestamps, error (if failed).

### Fetch Results
- **Endpoint**: `GET /api/rest/jobs/{job_id}/results` or GraphQL interface `POST /api/gql`
- **Filters**: `gene`, `perturbation_type`, `donor`, `cell_type`, `cursor`, `limit`.
- **Response**: Paginated (if suitable) per-cell embeddings and distance metrics. For GraphQL, the endpoint consumer can request the exact desired data from the graph structure.

## 8. Scalability Plan

- **Queue + worker model**: The API enqueues perturbation jobs. Stateless workers (e.g. AWS Lambda) process perturbation batches and write outputs. This scales up and down for variable workloads.

- **Storage design for large jobs**: Metadata in a relational DB; large embedding matrices in columnar/object storage with references in DB. Regionally separated backups support disaster recovery.

- **Expected bottlenecks**: Model inference throughput, DB write amplification, and retrieval latency for large embedding payloads.
  - *Mitigations*: Worker autoscaling, batching/chunking, partitioned storage, result caching, async query endpoints.

## 9. Deployment Plan

- **Containerisation approach**: Separate containers for API, workers, and DB adapter services.

- **Runtime/orchestrator (`k8s`/`ECS`/etc.)**:
  - *Smaller scales*: A scheduler VM that can request serverless Lambda instances, along with a separate VM for API handling, may be sufficient.
  - *Larger scales*: Kubernetes with separate node pools for CPU API pods and GPU worker pods is more reliable and worth the added complexity trade-off.

- **GPU worker allocation approach**: Queue-based scheduling with resource requests/limits and dedicated GPU worker deployment.

- **Basic observability (`logs`/`metrics`)**: Structured logs, queue depth metrics, worker throughput, error rates, latency dashboards.
