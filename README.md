# Helical Tech Test

This is a Django-based application that simulates an in-silico perturbation pipeline.

It provides:
- a REST API to generate synthetic data and run the pipeline
- a GraphQL API to query stored results
- a Django admin interface to inspect database records

Data is stored in an `SQLite` database via the Django ORM.

## Running the application

**Prerequisite**: Docker (or Podman) installed on the host system.

From the repository root, start the application with:

`docker compose up --build`

## Usage

### 1) Verify the server is running

Open:

> `http://localhost:8000/api/rest/healthcheck`

You should receive: `success`.

### 2) Generate sample pipeline output

**REST**

To access the OpenAPI docs, where you can run the demo endpoint, navigate to:

> `http://localhost:8000/api/rest/docs`

Run `POST /api/rest/demo` with query parameters.

- **Recommended demo (default)**:
  - `obs=1000`
  - `vars=500`
  - `perts=100`

- **Larger demo (optional)**:
  - `obs=1000`
  - `vars=500`
  - `perts=300`

- **Stress test (optional, may be slow/fail on low-resource machines)**:
  - `obs=1000`
  - `vars=500`
  - `perts=1500`

### 3) View outputs

**GraphQL**

To access the GraphiQL browser, where you can construct and test GraphQL queries, navigate to:

> `http://localhost:8000/api/gql`

**Django Admin**

To access the Django Admin panel, where you can view SQLite database records and manually alter them, navigate to:

> `http://localhost:8000/admin`

You can log in with username: `admin`, and password: `1234`.

## Notes

- The current Docker setup is ephemeral by default. Data may be lost when the container is removed/recreated (for example after `docker compose down`).
- If the database is empty, call `POST /api/rest/demo` again to generate fresh sample data.
- For changes to code to be applied, the container will need to be rebuilt and launched with `docker compose up --build`. Beware that all data in the container will be lost.
- With `512`-dim embeddings stored in SQLite `JSONField`, higher `perts` values substantially increase write time and DB size. For local runs, reduce `perts` first if performance degrades.
