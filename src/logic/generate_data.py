import random
import string

import anndata as ad
from django.db import OperationalError
import numpy as np
import pandas as pd
import scipy.sparse as spsparse

from logic.consts import GENE_POOL_SIZE
from logic.types import PertSpec
from server.db import models

# track total_obs_count to ensure unique cell labels between
# data generations for demo purposes (assume DB empty on start)
total_obs_count = 0
total_batch_count = 0

# options for categorical metadata
cell_type_list = ["B", "T", "Monocyte"]
donor_list = [f"Patient {p}" for p in string.ascii_uppercase]
chromosome_list = [f"{i:0>2d}" for i in range(1, 23)] + ["X", "Y"]


# Pool from which to randomly select genes on each data generation.
try:
    gene_pool = [
        models.Gene(
            label=f"Gene_{i:05d}",
            symbol="".join(random.choices(string.ascii_uppercase + string.digits, k=6)),
            chromosome=random.choice(chromosome_list),
        )
        for i in range(GENE_POOL_SIZE)
    ]
    print("Creating gene pool...")
    models.Gene.objects.bulk_create(gene_pool)
    print("Done")
except OperationalError as err:
    print(err)


def generate_random_data(
    obs_count: int, var_count: int, pert_count: int
) -> tuple[ad.AnnData, list[PertSpec]]:
    global total_obs_count
    global total_batch_count
    # create main body of data
    counts = spsparse.csc_matrix(
        np.random.poisson(1, size=(obs_count, var_count)),
        dtype=np.float32,
    )
    adata = ad.AnnData(counts)

    # select random sample of genes from available var_pool (order maintained)
    var_idxs = sorted(random.sample(range(len(gene_pool)), var_count))
    genes = [gene_pool[i] for i in var_idxs]

    pert_pool: list[PertSpec] = []
    for gene in genes:
        for ptype in ("KO", "AC", "OE"):
            pert_pool.append(PertSpec(ptype, gene.label))

    pert_idxs = sorted(random.sample(range(len(pert_pool)), pert_count))
    perts = [pert_pool[i] for i in pert_idxs]

    # add obs and var labels
    adata.obs_names = [
        f"Cell_{i:06d}"
        for i in range(
            total_obs_count,
            total_obs_count + adata.n_obs,
        )
    ]
    adata.var_names = [g.label for g in genes]

    # add obs metadata
    cell_type = np.random.choice(cell_type_list, size=(adata.n_obs,))
    adata.obs["cell_type"] = pd.Categorical(cell_type)
    donor = np.random.choice(donor_list, size=(adata.n_obs,))
    adata.obs["donor"] = pd.Categorical(donor)
    adata.obs["batch"] = [f"Batch_{total_batch_count:03d}" for _ in range(adata.n_obs)]

    # add var metadata
    gene_symbol = [g.symbol for g in genes]
    adata.var["gene_symbol"] = gene_symbol
    chromosome = [v.chromosome for v in genes]
    adata.var["chromosome"] = pd.Categorical(chromosome)

    total_obs_count += adata.n_obs
    total_batch_count += 1

    return adata, perts
