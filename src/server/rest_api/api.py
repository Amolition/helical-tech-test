from typing import Literal

from django.http import HttpRequest
from ninja import NinjaAPI

from logic.consts import BATCH_SIZE, GENE_POOL_SIZE
from logic.generate_data import generate_random_data
from logic.process_data import pipeline

from .utils import handle_err

api = NinjaAPI()


@api.get("healthcheck")
@handle_err
def get_healthcheck(request: HttpRequest) -> Literal["success"]:
    """Check if server is alive.

    **GET**:
        `/api/rest/healthcheck`

    **Returns**:

        Always returns literal string `success`
    """
    return "success"


@api.post("demo")
@handle_err
def post_demo(request: HttpRequest, obs: int, vars: int, perts: int):
    """Generates demo anndata which is then fed through the modelling pipeline.

    **POST**:
        `/api/rest/demo`

    **Args**:

        *obs*:
            Number of obs/cells in generated data (incremented each call).

        *vars*:
            Number of vars/genes in generated data (chosen from a pool). The pool
            contains 1000 randomly generated genes which limits the maximum value
            of vars. This can be changed by modifying `VAR_POOL_SIZE` in
            `src/logic/consts.py`

        *perts*:
            Number of perturbations to apply. Selected randomly from available
            genes and perturbation type (knockout, activation or overexpression).
            Hence maximum allowed is 3x `vars`.

    **Returns**:

        null
    """
    assert vars <= GENE_POOL_SIZE, (
        f"vars ({vars}) must not exceed VAR_POOL_SIZE ({GENE_POOL_SIZE})"
    )
    assert perts <= vars * 3, (
        f"perts ({perts}), must not exceed three times vars ({vars})"
    )
    adata, specs = generate_random_data(obs, vars, perts)
    pipeline(adata, specs, BATCH_SIZE)
