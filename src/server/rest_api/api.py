from typing import Literal

from django.http import HttpRequest
from ninja import NinjaAPI

from logic.consts import BATCH_SIZE
from logic.generate_data import generate_random_data
from logic.process_data import pipeline

from .utils import handle_err

api = NinjaAPI()


@api.get("healthcheck")
@handle_err
def get_healthcheck(request: HttpRequest) -> Literal["success"]:
    """Check if server is alive.

    GET:
        `/api/rest/healthcheck`

    Returns:
        Always returns literal string `success`
    """
    return "success"


@api.post("demo")
@handle_err
def post_demo(request: HttpRequest, obs: int, vars: int, perts: int):
    adata, specs = generate_random_data(obs, vars, perts)
    pipeline(adata, specs, BATCH_SIZE)
