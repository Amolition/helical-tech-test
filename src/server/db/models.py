import uuid

from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Cell(BaseModel):
    label = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=100)
    donor = models.CharField(max_length=100)
    batch = models.CharField(max_length=100)

    class Meta:  # pyright:ignore [reportIncompatibleVariableOverride]
        ordering = ["label"]


class Gene(BaseModel):
    CHROMOSOME_CHOICES = [
        *[(f"{i:02d}", f"{i:02d}") for i in range(1, 23)],
        ("X", "X"),
        ("Y", "Y"),
    ]
    label = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=10, unique=True)
    chromosome = models.CharField(max_length=2, choices=CHROMOSOME_CHOICES)

    class Meta:  # pyright:ignore [reportIncompatibleVariableOverride]
        ordering = ["label"]


class Expression(BaseModel):
    cell = models.ForeignKey(Cell, related_name="expressions", on_delete=models.PROTECT)
    gene = models.ForeignKey(Gene, related_name="expressions", on_delete=models.PROTECT)
    value = models.FloatField()

    class Meta:  # pyright:ignore [reportIncompatibleVariableOverride]
        ordering = ["cell__label", "gene__label"]


class Embedding(BaseModel):
    PERTURBATION_TYPE_CHOICES = [
        ("KO", "Knockout"),
        ("AC", "Activation"),
        ("OE", "Overexpression"),
        ("NA", "None"),
    ]
    cell = models.ForeignKey(
        Cell,
        related_name="embeddings_for_cell",
        on_delete=models.PROTECT,
    )
    perturbation_gene = models.ForeignKey(
        Gene,
        blank=True,
        null=True,
        related_name="embeddings_where_perturbed",
        on_delete=models.PROTECT,
    )
    perturbation_type = models.CharField(
        max_length=2,
        choices=PERTURBATION_TYPE_CHOICES,
    )
    value = models.JSONField()
    dist = models.FloatField()

    class Meta:  # pyright:ignore [reportIncompatibleVariableOverride]
        ordering = ["cell__label", "perturbation_gene__label", "perturbation_type"]
