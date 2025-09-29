from rest_framework import serializers

class BoundingBoxSerializer(serializers.Serializer):
    top_left = serializers.ListField(
        child=serializers.FloatField(), 
        min_length=2, 
        max_length=2
    )
    top_right = serializers.ListField(
        child=serializers.FloatField(), 
        min_length=2, 
        max_length=2
    )
    bottom_left = serializers.ListField(
        child=serializers.FloatField(), 
        min_length=2, 
        max_length=2
    )
    bottom_right = serializers.ListField(
        child=serializers.FloatField(), 
        min_length=2, 
        max_length=2
    )

    # def validate(self, data):
        # return data