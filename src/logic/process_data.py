import anndata as ad
from django.db import transaction
import numpy as np
from pandas import DataFrame
from scipy.sparse import csc_matrix

from logic.consts import EMBEDDING_LENGTH
from logic.types import PertSpec
from server.db import models


def run_model(adata: ad.AnnData) -> np.ndarray:
    return np.random.rand(adata.n_obs, EMBEDDING_LENGTH) * 10 - 5


def gen_perturbed_adata(
    adata: ad.AnnData,
    specs: list[PertSpec],
):
    for spec in specs:
        # backup column to be mutated
        orig = adata[:, spec.gene].X
        assert isinstance(orig, csc_matrix)
        orig_copy = orig.copy()
        try:
            # mutate column defined by spec in-place
            match spec.ptype:
                case "KO":
                    adata[:, spec.gene] = 0
                case "AC":
                    adata[:, spec.gene] = 2
                case "OE":
                    adata[:, spec.gene] = 5
            yield spec, adata
        finally:
            # restore column to original data
            adata[:, spec.gene] = orig_copy


def calc_cosine_dist(
    base_emb_arr: np.ndarray,
    pert_emb_arr: np.ndarray,
):
    dot = np.einsum("ij,ij->i", base_emb_arr, pert_emb_arr)
    base_emb_arr_norm = np.linalg.norm(base_emb_arr, axis=1)
    pert_emb_arr_norm = np.linalg.norm(pert_emb_arr, axis=1)

    return np.clip(1 - dot / (base_emb_arr_norm * pert_emb_arr_norm), 0, 2)


def pipeline(
    adata: ad.AnnData,
    specs: list[PertSpec],
    batch_size: int,
):
    print("Pipeline activated")

    # retrieve genes from DB
    print("Retrieving Genes from DB...")
    genes = list(models.Gene.objects.filter(label__in=adata.var_names))
    genes_dict = {g.label: g for g in genes}
    print("Done")

    # add cells to DB if not present (including expression info and base embedding)
    print("Processing Cells info...")
    cells: list[models.Cell] = []
    cells_dict: dict[str, models.Cell] = {}
    expressions: list[models.Expression] = []
    base_emb_arr = run_model(adata)
    embeddings: list[models.Embedding] = []
    assert isinstance(adata.obs, DataFrame)
    assert isinstance(adata.X, csc_matrix)
    for c, t, d, b, g_idxs, vals, *emb in np.column_stack(
        [
            adata.obs_names.to_numpy(),
            adata.obs.to_numpy(),
            adata.X.tolil().rows,
            adata.X.tolil().data,
            base_emb_arr,
        ]
    ):
        cell = models.Cell(label=c, type=t, donor=d, batch=b)
        cells.append(cell)
        cells_dict[c] = cell
        expressions.extend(
            [
                models.Expression(cell=cell, gene=genes[g_idxs[i]], value=vals[i])
                for i in range(len(vals))
            ]
        )
        g_idx_set = set(g_idxs)
        zero_genes = [g for i, g in enumerate(genes) if i not in g_idx_set]
        expressions.extend(
            [models.Expression(cell=cell, gene=g, value=0) for g in zero_genes]
        )
        embeddings.append(
            models.Embedding(
                cell=cell,
                perturbation_gene=None,
                perturbation_type="NA",
                value=emb,
                dist=0,
            )
        )
    print("Done")
    print("Adding Cells to DB...")
    with transaction.atomic():
        models.Cell.objects.bulk_create(cells, batch_size=2000)
        models.Expression.objects.bulk_create(expressions, batch_size=2000)
        models.Embedding.objects.bulk_create(embeddings, batch_size=2000)
    print("Done")

    # modify batch size to take into account number of cells per adata object
    cells_count = max(1, len(cells))
    mod_batch_size = max(1, batch_size // cells_count)

    # iterate through perturbations in batches to control db access frequency
    # in exchange for small mem tradeoff of holding extra embeddings before saving
    total_ops = len(specs) * len(cells)
    progress_step = max(1, total_ops // 10)
    ops_count = 0
    batch_count = 0
    while specs:
        spec_batch, specs = (specs[:mod_batch_size], specs[mod_batch_size:])
        pert_adata_batch = gen_perturbed_adata(adata, spec_batch)
        pert_embs: list[models.Embedding] = []
        for pert_spec, pert_adata in pert_adata_batch:
            pert_emb_arr = run_model(pert_adata)
            pert_dist_arr = calc_cosine_dist(base_emb_arr, pert_emb_arr)
            for c, dist, *emb in np.column_stack(
                [
                    pert_adata.obs_names.to_numpy(),
                    pert_dist_arr,
                    pert_emb_arr,
                ]
            ):
                pert_embs.append(
                    models.Embedding(
                        cell=cells_dict[c],
                        perturbation_gene=genes_dict[pert_spec.gene],
                        perturbation_type=pert_spec.ptype,
                        value=emb,
                        dist=dist,
                    )
                )
                ops_count += 1
                if not ops_count % progress_step:
                    print(f"progress: {ops_count / total_ops:.0%}")

        # add embeddings in bulk once per batch
        batch_count += 1
        print(f"Adding Embedding Batch #{batch_count} to DB...")
        models.Embedding.objects.bulk_create(pert_embs)
        print("Done")

    print("Pipeline Complete")
