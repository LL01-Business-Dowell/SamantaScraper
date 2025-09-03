from django.urls import path
from .views import GeoQueryView

urlpatterns = [
    path('geo-query/', GeoQueryView.as_view(), name='geo-query'),
]