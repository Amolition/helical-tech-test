from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4
import uuid
import numpy as np
from scipy import spatial as spspatial
import anndata as ad

from demo.generate_data import generate_random_data


def run_model(adata: ad.AnnData) -> np.ndarray:
    return np.random.rand(adata.n_obs, 3) * 10 - 5


@dataclass
class PertSpec:
    ptype: Literal["knockout", "activation", "overexpression"]
    gene: str


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
            match spec.ptype:
                case "knockout":
                    pert_adata[:, [spec.gene]] = 0
                case "activation":
                    pert_adata[:, [spec.gene]] = 2
                case "overexpression":
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
    adata_id = uuid4()

    # save adata
    print(adata_id, adata)

    base_id = uuid4()
    base_spec = None
    base_emb_arr = run_model(adata)
    base_emb_dist = 0

    # save base data
    print((base_id, base_spec, base_emb_arr, base_emb_dist))

    pert_adata_batches = gen_perturbed_adata(adata, specs, batch_size)
    for pert_adata_batch in pert_adata_batches:
        pert_emb_batch: list[tuple[UUID, PertSpec, np.ndarray, np.ndarray]] = []
        for pert_spec, pert_adata in pert_adata_batch:
            pert_id = uuid4()
            pert_emb_arr = run_model(pert_adata)
            pert_emb_dist = calc_cosine_dist(base_emb_arr, pert_emb_arr)
            pert_emb_batch.append((pert_id, pert_spec, pert_emb_arr, pert_emb_dist))

        # save a batch of data in one transaction
        for i, x in enumerate(pert_emb_batch):
            print(i)
            for y in x:
                print(y)


def testing():
    specs = [PertSpec("overexpression", "Gene_0001")]
    adata = generate_random_data(3, 5)
    pipeline(adata, specs, 10)


testing()


# NOTE:
# - make ORM but don't bother with REST/GraphQL API, just mention it in write up
# -- first just do print statements and replace with db/orm later
# - make example file to put these functions together with generated data
