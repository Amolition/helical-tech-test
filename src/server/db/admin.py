from django.contrib import admin
from .models import Cell, Gene, Expression, Embedding

admin.site.register([Cell, Gene, Expression, Embedding])
