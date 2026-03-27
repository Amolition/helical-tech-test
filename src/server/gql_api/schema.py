import strawberry
import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension

from .types import Cell, Gene, Expression, Embedding


@strawberry.type
class Query:
    cells: list[Cell] = strawberry_django.field()
    genes: list[Gene] = strawberry_django.field()
    expressions: list[Expression] = strawberry_django.field()
    embeddings: list[Embedding] = strawberry_django.field()


schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension,
    ],
)
