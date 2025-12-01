import traceback
import json

print("\n=== LOADING VIEWS.PY ===")

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BoundingBoxSerializer

# Load Datacube query function
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
    OLD Mongo-based endpoint (deprecated).
    """
    def post(self, request):
        return Response(
            {"error": "MongoDB geospatial query is deprecated. Use /api/datacube/"},
            status=status.HTTP_400_BAD_REQUEST
        )


class GeoQueryViewDatacube(APIView):
    """
    Datacube-optimized geospatial lookup API.
    """
    def post(self, request):
        print("\n=== /api/geo-query-cube/ called ===")
        print("Incoming request data:", request.data)

        serializer = BoundingBoxSerializer(data=request.data)

        if not serializer.is_valid():
            print("\n=== Serializer Validation Failed ===")
            print(serializer.errors)
            return Response(
                {"error": "Invalid coordinates", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        print("Validated data:", data)

        try:
            print("\n=== Calling Datacube Query ===")
            results = query_by_four_corners_datacube(
                top_left=data["top_left"],
                top_right=data["top_right"],
                bottom_left=data["bottom_left"],
                bottom_right=data["bottom_right"],
            )

            print("Datacube result:", results)
            print("=== Datacube Query Finished Successfully ===\n")

            return Response({"result": results}, status=200)

        except Exception as e:
            print("\n=== ERROR IN Datacube Query ===")
            traceback.print_exc()
            print("=========================================\n")

            return Response(
                {
                    "error": "Datacube query failed",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
