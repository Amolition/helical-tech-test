# ISP Pipeline Design

**Sections 1-6 relate primarily to Part 1, whilst Sections 7-9 relate primarily to Part 2.**

## 1. Overview

- **What this pipeline does**: Generate synthetic single-cell expression data, apply perturbations (`KO`/`AC`/`OE`), run a mock model to produce embeddings, and compute distances versus baseline.

- **What is mocked**: Model inference is mocked (`run_model`) and returns random embeddings; no real foundation model integration. Data is saved to an ephemeral database that is destroyed when the container is removed/recreated.

- **What scale this demo uses**: Data scale can be varied using fixed parameters in `src/logic/consts.py` and request parameters submitted to `POST /api/rest/demo`. Perturbations are processed sequentially because each run mutates a shared `AnnData` in-place and then restores it. This preserves state isolation and keeps peak memory low. Local demo runs use reduced perturbation counts for practical execution time and DB size, while preserving the required `512`-dim embedding contract.

- **How to adapt for larger scales**: For larger workloads, the same logic could be parallelised by partitioning perturbation conditions across isolated workers. Each worker handles a separate data shard and writes embeddings/distances asynchronously to shared storage.

- **How to generate and inspect outputs**: Follow `README.md` to run the application with Docker, call `POST /api/rest/demo` to generate sample results, and inspect/query outputs via GraphQL (`POST /api/gql`) or the Django admin UI.

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
  - *Downstream analysis*: Embeddings and distances are queryable from the relational DB via GraphQL requests, though the storage format is not yet optimised for large-scale analytics.

- **Storage scalability caveat**: Storing vectors in `Embedding.value` as `JSONField` is a demo-friendly choice, but it is not optimal for large-scale analytics (e.g. clustering or differential analysis). At production scale, embeddings would be better placed in columnar/object or vector-optimised storage, with indexed references in the relational DB.

## 4. Memory & Trade-offs

- **Peak memory during**:
  1. Baseline embedding run: one base `AnnData` matrix plus one baseline embedding array (`n_cells x embedding_dim`).
  2. Perturbation run: one temporary backup of a single target gene column, the same shared `AnnData` mutated in-place, and one perturbed embedding array.
  3. Persistence phase: in-memory `Embedding` ORM objects accumulated per `batch_size` before bulk insert.

- **Illustrative memory example**:
  - *Assumptions*: `n_cells = 50,000`, `n_genes = 20,000`, embedding dim `= 512`, `float32` (`4 bytes/value`), `15,000` perturbation conditions.
  - *One full expression matrix* (`50,000 x 20,000`) is ~`4.0 GB` dense (`50,000 * 20,000 * 4 bytes`), matching the task statement.
  - *One embedding array per condition* (`50,000 x 512`) is ~`100 MB`.
  - *Baseline + one perturbed embedding array in memory at once* is ~`200 MB` (excluding Python/ORM overhead).
  - *If all perturbation embeddings were materialised simultaneously*, raw embedding payload would be ~`1.5 TB` (`100 MB * 15,000`), which motivates streaming/batched writes.
  - *In-place perturbation memory profile*: Matrix memory remains near one shared base matrix + one temporary gene-column backup, instead of one full copied matrix per condition.
  - *Distance-only footprint*: storing one `float32` distance per cell per condition is ~`3.0 GB` raw (`50,000 * 15,000 * 4 bytes`), far smaller than full embeddings but still non-trivial.

- **Memory strategy**: Perturbations are applied to one gene column at a time on a shared matrix and then restored in a `try/finally` block, which avoids creating full `AnnData` copies per condition.

- **Main trade-offs made**:
  - *Memory vs speed*: in-place mutation greatly reduces RAM use compared with per-perturbation matrix copies, but adds per-iteration restore overhead.
  - *Execution model constraint*: The model needs to be run sequentially (not concurrently / in parallel) since only one perturbation exists at a time.
  - *DB throughput vs RAM*: batching writes with `bulk_create` improves insert performance but increases temporary memory usage as `batch_size` grows.
  - *Semantic completeness vs storage cost*: The persistence logic writes explicit zero-valued `Expression` rows so that "measured zero" is distinguishable from "not measured" for each cell-gene pair. This improves interpretability and query semantics, but increases write volume and storage footprint at larger scales.
  - *Potential optimisation path*: At larger scales, this can be replaced with sparse-only storage plus an explicit measurement-status flag (or equivalent metadata) to preserve semantic clarity with lower storage overhead.

- **Practical implication**: Peak matrix memory is close to base matrix + one column backup. Most tunable memory pressure comes from embedding buffers and DB write batch size.

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

- **ORM optimisation notes**: Django ORM handles many memory and DB access optimisations. Further improvements could include manually written SQL for specific complex cases.

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

- **Example request**:
  ```json
  {
    "dataset_id": "demo_dataset_v1",
    "perturbations": [
      {"gene": "Gene_00010", "type": "KO"},
      {"gene": "Gene_00042", "type": "OE"}
    ],
    "filters": {
      "donor": ["Patient C"],
      "cell_type": ["T"]
    }
  }
  ```

- **Example response**:
  ```json
  {
    "job_id": "job_01JABCXYZ",
    "status": "queued",
    "submitted_at": "2026-03-27T12:00:00Z"
  }
  ```

### Check Status
- **Endpoint**: `GET /api/rest/jobs/{job_id}`
- **Response**: `status`, `progress`, timestamps, error (if failed).

- **Example response**:
  ```json
  {
    "job_id": "job_01JABCXYZ",
    "status": "running",
    "progress": 0.42,
    "started_at": "2026-03-27T12:00:10Z",
    "updated_at": "2026-03-27T12:02:00Z",
    "error": null
  }
  ```

### Fetch Results
- **Endpoint**: `GET /api/rest/jobs/{job_id}/results` or GraphQL via `/api/gql` (GraphiQL UI in browser or POST requests)
- **Filters**: `gene`, `perturbation_type`, `donor`, `cell_type`, `cursor`, `limit`.
- **Response**: Paginated (if suitable) per-cell embeddings and distance metrics. For GraphQL, the endpoint consumer can request the exact desired data from the graph structure.

- **Example response**:
  ```json
  {
    "job_id": "job_01JABCXYZ",
    "items": [
      {
        "cell_label": "Cell_000123",
        "perturbation_gene": "Gene_00010",
        "perturbation_type": "KO",
        "dist": 0.183,
        "embedding": [0.12, -0.44, 0.91, ...]
      }
    ],
    "next_cursor": "cursor_abc123"
  }
  ```

## 8. Scalability Plan

- **Queue + worker model**: The API enqueues perturbation jobs. Stateless workers (e.g. AWS Lambda) process perturbation batches and write outputs. This supports scaling up and down for variable workloads.

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
