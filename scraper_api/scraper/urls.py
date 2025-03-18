from django.urls import path
from .views import search_google_maps

urlpatterns = [
    path("search/", search_google_maps, name="search_google_maps"),
]
