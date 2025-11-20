import traceback
print("\n=== LOADING VIEWS.PY ===")

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BoundingBoxSerializer
# from .queries import query_by_four_corners_datacube
try:
    from .queries import query_by_four_corners_datacube
    print("Imported queries successfully")
except Exception as e:
    print("\n=== ERROR IMPORTING QUERIES ===")
    traceback.print_exc()
    print("================================\n")
    raise




class GeoQueryView(APIView):
    """
    OLD Mongo-based endpoint.
    Mongo lookup is no longer supported because query_by_four_corners
    has been removed from queries.py.
    """
    def post(self, request):
        return Response(
            {"error": "Mongo DB geospatial query is no longer supported. Use /api/datacube/ instead."},
            status=status.HTTP_400_BAD_REQUEST
        )


class GeoQueryViewDatacube(APIView):
    """
    NEW endpoint that performs optimized Datacube lookups.
    """
    def post(self, request):
        serializer = BoundingBoxSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            results = query_by_four_corners_datacube(
                top_left=serializer.validated_data["top_left"],
                top_right=serializer.validated_data["top_right"],
                bottom_left=serializer.validated_data["bottom_left"],
                bottom_right=serializer.validated_data["bottom_right"]
            )
            return Response(results)

        except Exception as e:
            return Response(
                {"Datacube error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
