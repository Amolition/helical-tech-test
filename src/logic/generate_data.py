from dataclasses import dataclass
import random
import string
from typing import Literal
import numpy as np
import scipy.sparse as spsparse
import pandas as pd
import anndata as ad

# track total_obs_count to ensure unique cell labels if called multiple times
total_obs_count = 0

# options for categorical metadata
cell_type_list = ["B", "T", "Monocyte"]
donor_list = [f"Patient {p}" for p in string.ascii_uppercase]
chromosome_list = [f"{i:0>2d}" for i in range(1, 23)] + ["X", "Y"]


@dataclass
class Var:
    label: str
    symbol: str
    chromosome: str


# pool from which to randomly select genes on each data generation
var_pool = [
    Var(
        f"Gene_{i:05d}",
        "".join(random.choices(string.ascii_uppercase + string.digits, k=6)),
        random.choice(chromosome_list),
    )
    for i in range(10000)
]


def generate_random_data(obs_count: int, var_count: int) -> ad.AnnData:
    global total_obs_count
    # create main body of data
    counts = spsparse.csr_matrix(
        np.random.poisson(1, size=(obs_count, var_count)),
        dtype=np.float32,
    )
    adata = ad.AnnData(counts)

    # select random sample of genes from available var_pool (order maintained)
    var_idxs = sorted(random.sample(range(len(var_pool)), var_count))
    vars = [var_pool[i] for i in var_idxs]

    # add obs and var labels
    adata.obs_names = [
        f"Cell_{i:06d}"
        for i in range(
            total_obs_count,
            total_obs_count + adata.n_obs,
        )
    ]
    adata.var_names = [v.label for v in vars]

    # add obs metadata
    cell_type = np.random.choice(cell_type_list, size=(adata.n_obs,))
    adata.obs["cell_type"] = pd.Categorical(cell_type)
    donor = np.random.choice(donor_list, size=(adata.n_obs,))
    adata.obs["donor"] = pd.Categorical(donor)

    # add var metadata
    gene_symbol = [v.symbol for v in vars]
    adata.var["gene_symbol"] = gene_symbol
    chromosome = [v.chromosome for v in vars]
    adata.var["chromosome"] = pd.Categorical(chromosome)

    total_obs_count += adata.n_obs

    return adata
