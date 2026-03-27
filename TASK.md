# Helical Software Development

# Challenge

## In-Silico Perturbation Pipeline

**Time budget:** ~4–6 hours
**Language:** Python (libraries of your choice)
**Deliverable:** A Git repository containing your code, sample outputs, and a short design
document (markdown, diagrams, or comments in code — whatever communicates clearly)

## Context

Helical's platform lets pharmaceutical researchers run **In-Silico Perturbation (ISP)**
experiments. The workflow: take a population of cells represented as a gene expression matrix,
simulate what happens when you knock out or overexpress specific genes, run the perturbed
data through a foundation model to obtain embeddings, and compare those embeddings
against a healthy baseline.

The foundation model is a **black box**. It accepts an AnnData object and returns embeddings.
You don't need to understand or modify the model. Your job is everything around it: how the
data is structured going in, how the results are structured coming out, and how the whole thing
holds together when a client wants to run it at real scale.
We work with the **AnnData** format (`.h5ad`), which is the standard in single-cell biology.

## Scenario

A pharma client wants to run ISP on:

- **50,000 cells** (from multiple donors and cell types)
- **5,000 target genes** (each gene is perturbed independently)
- **3 perturbation types per gene** (knockout, overexpression, activation)

That's **15,000 perturbation conditions**. For each condition, the model takes an AnnData of all
50k cells (with the perturbation applied to the expression values) and returns one embedding
vector per cell.
The task is to design a pipeline which is efficient in memory as well as clear to the developers.
Should the input data be modified or prepared for the task? Where is the output saved and
retrieved efficiently for display and downstream tasks?


## 1. Design & Implementation

### 1.1. Design

Address the following in a write-up (markdown, diagrams, or pseudocode — whatever
communicates clearly):

**Input data:**
How should the perturbed expression data be structured before it goes to the model? A single
uncompressed 50k × 20k float32 matrix is ~4 GB — how do you avoid materialising 15,
copies of it?

**Output data:**
The model returns a 512-dimensional embedding per cell per perturbation condition. How do
you store and organise the results so they can be queried efficiently — both for display (a
researcher browsing results) and for downstream computation (clustering, differential analysis)?

**Memory profile:**
Walk through the peak memory footprint of your design and the trade-offs you're making
between query speed, memory, and storage.

### 1.2. Implementation

Build a working pipeline that demonstrates your design. Use **synthetic data** — you don't need
the real Helical package or a real model. The point is to show that your data structures and
pipeline logic actually work. To get inspired how data can look like, you can check this link.

**Generate synthetic input data:**
Create an AnnData object with a realistic shape (you can scale down for practical purposes, e.g.
1,000 cells × 500 genes). Include meaningful `obs` (cell type, donor, batch) and `var` (gene
symbol, chromosome) metadata.

**Mock the model:**
Write a function with the signature:

```python
def run_model(adata: AnnData) -> np.ndarray
```

that returns a random embedding matrix of shape `(n_cells, 512)`. It should accept an AnnData
and return embeddings — the internals don't matter.

**Run perturbations**
Implement the loop that:

- Takes a list of perturbation specs (gene, perturbation type)
- Applies each perturbation to the expression data
- Calls the mock model
- Collects and stores the embeddings in the structure you designed

**Compute comparisons**
For each perturbation condition, compute a simple distance metric (e.g., cosine distance)
between the perturbed embeddings and the healthy baseline embeddings. Store the results.

**Query the results**
Show that you can answer at least these queries from your output:
    - How do you organise the embeddings so they can be retrieved efficiently — both for
       display (a researcher browsing results in a UI) and for downstream computation (e.g.,
       clustering, differential analysis)?
    - If a researcher asks "show me the embedding shift for gene X, knockout, in donor 3's
       T-cells" — can your structure answer that query without loading everything into memory?
    - How do you store the comparison results (distances or scores against the healthy
       baseline)?

**What we're looking** for is that the code **runs** and produces correct output, that your design and
implementation are consistent (you built what you described), clean readable code, and
sensible handling of data at the scale you chose.

## 2. API Design & Architecture

Provide a brief architectural write-up (a page or diagram is fine) that covers:

**API contract**
Define the REST (or GraphQL) endpoints for the perturbation workflow: creating a job, checking
status, fetching results. Include request/response schemas.

**Scalability story**
How would this system handle 50 concurrent users each launching 1,000-perturbation jobs?
Sketch the queue, worker, and storage design. What breaks first and how do you address it?


**Deployment considerations**
Briefly describe how you'd containerise and deploy this (Docker, k8s, ECS — your choice). How
do you handle GPU resource allocation for inference workers?

**Submission**
Push your work to a Git repository (GitHub, GitLab, or a zip). We expect:
```
├── README.md # How to run it, any setup notes
├── design.md # Your write-ups for Part 1 (design) and Part 2
├── src/ # Pipeline code (Part 1 implementation)
│ ├── generate_data.py # Synthetic data generation
│ ├── pipeline.py # Main pipeline logic
│ └── ...
├── notebooks/ (optional) # Exploration, plots, query demos
└── outputs/ (optional) # Sample results
```
Spend your time where it counts. A clear design with simple working code beats an over-built
framework with a vague write-up.
If you have any questions, do not hesitate to ask via email! Good luck 🤗
**Your Helical Team**
