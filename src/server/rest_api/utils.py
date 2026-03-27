from functools import wraps
from typing import Any, Callable

from django.http import HttpResponseServerError


def handle_err(fn: Callable[..., Any]):
    @wraps(fn)
    def wrapper(*args: ..., **kwargs: ...):
        try:
            return fn(*args, **kwargs)
        except Exception as error:
            print(error)
            return HttpResponseServerError(error)

    return wrapper
