# Helical-Tech-Test

This is a django-based application that simulates in-silico perturbation modelling and data.

It provides a REST API endpoint to generate simulated data and process it, as well as a GraphQL API to view the processed data in a flexible structure. The data is saved to an SQLite database via the Django ORM.

## Running Application

**Prerequisite**: Docker (or Podman) installed on the host system

To start the application, simply run: `docker compose up` in the root folder of the repository.

## Usage

All interfaces can be accessed via browser.

### REST

To access the OPENAPI docs, where you can try the demo endpoint, navigate to:

> `localhost:8000/api/rest/docs`

### GraphQL

To access the GraphiQL browser, where you can construct and test GraphQL queries, navigate to:

> `localhost:8000/api/gql`


### Django Admin

To access the Django Admin panel, where you can view SQLite database records and manually alter them, navigate to:

> `localhost:8000/admin`

You can login with username: `admin`, and password: `1234`

## Notes

- The database is recreated each time the application is restarted, so it will initially be empty. To make sure you have some data available, call the `/api/rest/demo` endpoint at least once (most easily done by navigating to `localhost:8000/api/rest/docs`).
