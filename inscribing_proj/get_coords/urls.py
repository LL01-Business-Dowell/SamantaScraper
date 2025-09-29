from django.urls import path
from .views import GeoQueryView,GeoQueryViewDatacube

urlpatterns = [
    path('geo-query/', GeoQueryView.as_view(), name='geo-query'),
    path('geo-query-cube/', GeoQueryViewDatacube.as_view(), name='geo-query-cube')

]