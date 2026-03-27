from django.contrib import admin
from django.db.models import Model
from django.utils.html import format_html

from .models import BaseModel, Cell, Embedding, Expression, Gene


class BaseAdmin(admin.ModelAdmin):
    @admin.display(description="id")
    def monospace_id(self, obj: BaseModel):
        return format_html(
            "<span style='font-family: monospace' title='{}'>{}</span>",
            obj.id,
            str(obj.id)[:8],
        )


@admin.register(Cell)
class CellAdmin(BaseAdmin):
    list_display = ["label", "type", "donor", "batch", "created_at", "monospace_id"]


@admin.register(Gene)
class GeneAdmin(BaseAdmin):
    list_display = ["label", "symbol", "chromosome", "created_at", "monospace_id"]


@admin.register(Expression)
class ExpressionAdmin(BaseAdmin):
    list_display = ["cell__label", "gene__label", "value", "created_at", "monospace_id"]


@admin.register(Embedding)
class EmbeddingAdmin(BaseAdmin):
    list_display = [
        "cell__label",
        "perturbation_gene__label",
        "perturbation_type",
        "dist",
        "created_at",
        "monospace_id",
    ]
