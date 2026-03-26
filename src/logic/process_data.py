import warnings

import anndata as ad
import numpy as np
from pandas import DataFrame
from scipy.sparse import csr_matrix

from logic.consts import EMBEDDING_LENGTH
from logic.types import PertSpec
from server.db import models


def run_model(adata: ad.AnnData) -> np.ndarray:
    return np.random.rand(adata.n_obs, EMBEDDING_LENGTH) * 10 - 5


def gen_perturbed_adata(
    adata: ad.AnnData,
    specs: list[PertSpec],
    batch_size: int,
):
    while specs:
        spec_batch, specs = (specs[:batch_size], specs[batch_size:])
        pert_adata_batch: list[tuple[PertSpec, ad.AnnData]] = []
        for spec in spec_batch:
            pert_adata = adata.copy()
            # ignoring csr inefficiency warning with regard to sparse
            # matrix mutations since anndata not compatible with lil
            with warnings.catch_warnings(action="ignore"):
                match spec.ptype:
                    case "KO":
                        pert_adata[:, [spec.gene]] = 0
                    case "AC":
                        pert_adata[:, [spec.gene]] = 2
                    case "OE":
                        pert_adata[:, [spec.gene]] = 5
            pert_adata_batch.append((spec, pert_adata))
        yield pert_adata_batch


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
    # add genes to db if not present
    assert isinstance(adata.var, DataFrame)
    genes: list[models.Gene] = []
    genes_dict: dict[str, models.Gene] = {}
    for g, s, c in np.column_stack([adata.var_names.to_numpy(), adata.var.to_numpy()]):
        # assuming gene label is unique and consistent without checking for now
        gene, _ = models.Gene.objects.get_or_create(label=g, symbol=s, chromosome=c)
        genes.append(gene)
        genes_dict[g] = gene

    # add cells to db if not present (including expression info and base embedding)
    assert isinstance(adata.obs, DataFrame)
    assert isinstance(adata.X, csr_matrix)
    cells: list[models.Cell] = []
    cells_dict: dict[str, models.Cell] = {}
    base_emb_arr = run_model(adata)
    for c, t, d, g_idxs, vals, *emb in np.column_stack(
        [
            adata.obs_names.to_numpy(),
            adata.obs.to_numpy(),
            adata.X.tolil().rows,
            adata.X.tolil().data,
            base_emb_arr,
        ]
    ):
        # assuming cell label is unique and consistent without checking for now
        cell, created = models.Cell.objects.get_or_create(
            label=c,
            defaults={"type": t, "donor": d},
        )
        cells.append(cell)
        cells_dict[c] = cell
        if not created:
            continue
        models.Expression.objects.bulk_create(
            [
                models.Expression(cell=cell, gene=genes[g_idxs[i]], value=vals[i])
                for i in range(len(vals))
            ]
        )
        zero_genes = [g for i, g in enumerate(genes) if i not in g_idxs]
        models.Expression.objects.bulk_create(
            [models.Expression(cell=cell, gene=g, value=0) for g in zero_genes]
        )
        models.Embedding.objects.create(
            cell=cell,
            perturbation_gene=None,
            perturbation_type="NA",
            value=emb,
            dist=0,
        )

    pert_adata_batches = gen_perturbed_adata(adata, specs, batch_size)
    # iterate through perturbations in batches to control mem footprint
    for pert_adata_batch in pert_adata_batches:
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

        # add embeddings in bulk once per batch
        models.Embedding.objects.bulk_create(pert_embs)


# NOTE:
# - make example REST endpoints to put these functions together with generated data
# - make graphQL endpoint to see data easily
# - make dockerfile / compose file
# - write up the stuff as per the problem statement
