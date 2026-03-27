from strawberry import auto
import strawberry_django
from server.db import models


@strawberry_django.filter(models.Cell, lookups=True)
class CellFilter:
    id: auto
    created_at: auto
    label: auto
    type: auto
    donor: auto
    batch: auto
    expressions: "ExpressionFilter | None"
    embeddings_for_cell: "EmbeddingFilter | None"


@strawberry_django.order_type(models.Cell)
class CellOrder:
    created_at: auto
    label: auto
    type: auto
    donor: auto
    batch: auto
    expressions: "ExpressionOrder | None"
    embeddings_for_cell: "EmbeddingOrder | None"


@strawberry_django.type(
    models.Cell,
    filters=CellFilter,
    ordering=CellOrder,
)
class Cell:
    id: auto
    created_at: auto
    label: auto
    type: auto
    donor: auto
    batch: auto
    expressions: list["Expression"]
    embeddings_for_cell: list["Embedding"]


@strawberry_django.filter(models.Gene, lookups=True)
class GeneFilter:
    id: auto
    created_at: auto
    label: auto
    symbol: auto
    chromosome: auto
    expressions: "ExpressionFilter | None"
    embeddings_where_perturbed: "EmbeddingFilter | None"


@strawberry_django.order_type(models.Gene)
class GeneOrder:
    created_at: auto
    label: auto
    symbol: auto
    chromosome: auto
    expressions: "ExpressionOrder | None"
    embeddings_where_perturbed: "EmbeddingOrder | None"


@strawberry_django.type(
    models.Gene,
    filters=GeneFilter,
    ordering=GeneOrder,
)
class Gene:
    id: auto
    created_at: auto
    label: auto
    symbol: auto
    chromosome: auto
    expressions: list["Expression"]
    embeddings_where_perturbed: list["Embedding"]


@strawberry_django.filter(models.Expression, lookups=True)
class ExpressionFilter:
    id: auto
    created_at: auto
    value: auto
    cell: "CellFilter | None"
    gene: "GeneFilter | None"


@strawberry_django.order_type(models.Expression)
class ExpressionOrder:
    created_at: auto
    value: auto
    cell: "CellOrder | None"
    gene: "GeneOrder | None"


@strawberry_django.type(
    models.Expression,
    filters=ExpressionFilter,
    ordering=ExpressionOrder,
)
class Expression:
    id: auto
    created_at: auto
    value: auto
    cell: "Cell"
    gene: "Gene"


@strawberry_django.filter(models.Embedding, lookups=True)
class EmbeddingFilter:
    id: auto
    created_at: auto
    perturbation_type: auto
    value: auto
    dist: auto
    cell: "CellFilter | None"
    perturbation_gene: "GeneFilter | None"


@strawberry_django.order_type(models.Embedding)
class EmbeddingOrder:
    created_at: auto
    perturbation_type: auto
    value: auto
    dist: auto
    cell: "CellOrder | None"
    perturbation_gene: "GeneOrder | None"


@strawberry_django.type(
    models.Embedding,
    filters=EmbeddingFilter,
    ordering=EmbeddingOrder,
)
class Embedding:
    id: auto
    created_at: auto
    perturbation_type: auto
    value: auto
    dist: auto
    cell: "Cell"
    perturbation_gene: "Gene | None"
