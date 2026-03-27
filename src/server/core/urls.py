"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth.models import User
from django.db import IntegrityError, OperationalError
from django.urls import path
from strawberry.django.views import AsyncGraphQLView
from server.gql_api.schema import schema
from server.rest_api.api import api

try:
    # Create Admin User (for demo purposes only)
    User.objects.create_superuser("admin", None, "1234")
except IntegrityError as err:
    print(type(err))
except OperationalError as err:
    print(type(err))

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/rest/", api.urls),
    path("api/gql/", AsyncGraphQLView.as_view(schema=schema)),
]
