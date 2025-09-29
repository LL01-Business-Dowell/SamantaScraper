from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BoundingBoxSerializer
from .queries import query_by_four_corners, query_by_four_corners_datacube
from django.conf import settings

class GeoQueryView(APIView):
    def post(self, request):
        serializer = BoundingBoxSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            results = query_by_four_corners(
                top_left=serializer.validated_data['top_left'],
                top_right=serializer.validated_data['top_right'],
                bottom_left=serializer.validated_data['bottom_left'],
                bottom_right=serializer.validated_data['bottom_right']
                # mongo_uri=settings.MONGO_URI  # From settings
            )
            return Response(results)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class GeoQueryViewDatacube(APIView):
    def post(self, request):
        serializer = BoundingBoxSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            results = query_by_four_corners_datacube(
                top_left=serializer.validated_data['top_left'],
                top_right=serializer.validated_data['top_right'],
                bottom_left=serializer.validated_data['bottom_left'],
                bottom_right=serializer.validated_data['bottom_right']
            )
            return Response(results)
        except Exception as e:
            return Response(
                {"Datacube error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )