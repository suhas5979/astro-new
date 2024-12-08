
from rest_framework import serializers

class CustomerDetailsSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100, required=True)
    email = serializers.CharField(required=True)
    mobile_no = serializers.CharField(max_length=15, required=True)
    birth_time = serializers.TimeField(format='%H:%M', required=True)
    birth_date = serializers.DateField(required=True)
    birth_place = serializers.CharField(max_length=100, required=True) 
    latitude = serializers.DecimalField(max_digits=7, decimal_places=4, required=False)
    longitude = serializers.DecimalField(max_digits=7, decimal_places=4, required=False)

class CustomerDetailsLimitedSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    birth_date = serializers.DateField()
    birth_time = serializers.TimeField(format='%H:%M')
    birth_place = serializers.CharField(max_length=100)
    latitude = serializers.DecimalField(max_digits=7, decimal_places=4)
    longitude = serializers.DecimalField(max_digits=7, decimal_places=4)
