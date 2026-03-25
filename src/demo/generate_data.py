import random
import string
import numpy as np
import scipy.sparse as spsparse
import pandas as pd
import anndata as ad


def generate_random_data(obs_count: int, var_count: int) -> ad.AnnData:
    # create main body of data
    counts = spsparse.csr_matrix(
        np.random.poisson(1, size=(obs_count, var_count)),
        dtype=np.float32,
    )
    adata = ad.AnnData(counts)

    # add obs and var labels
    adata.obs_names = [f"Cell_{i:0>5d}" for i in range(adata.n_obs)]
    adata.var_names = [f"Gene_{i:0>4d}" for i in range(adata.n_vars)]

    # add obs metadata
    cell_type = np.random.choice(
        ["B", "T", "Monocyte"],
        size=(adata.n_obs,),
    )
    adata.obs["cell_type"] = pd.Categorical(cell_type)
    donor = np.random.choice(
        [f"Patient {p}" for p in ["A", "B", "C", "D"]],
        size=(adata.n_obs,),
    )
    adata.obs["donor"] = pd.Categorical(donor)

    # add var metadata
    gene_symbol = [
        "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        for _ in range(adata.n_vars)
    ]
    adata.var["gene_symbol"] = gene_symbol
    chromosome = np.random.choice(
        [f"{i:0>2d}" for i in range(1, 23)] + ["X", "Y"],
        size=(adata.n_vars,),
    )
    adata.var["chromosome"] = pd.Categorical(chromosome)

    return adata
