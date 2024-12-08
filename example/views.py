# example/views.py
from datetime import datetime
from django.conf import settings
import time
from requests.exceptions import RequestException
from django.db.models import Q
import aiohttp
from django.http import HttpRequest
import os
import json
from datetime import datetime
from pathlib import Path
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from decimal import Decimal, ROUND_HALF_UP
import time
from rest_framework import serializers
from django.conf import settings
import time
from requests.exceptions import RequestException
from django.db.models import Q
import aiohttp
import asyncio
from typing import Dict, Any, Tuple, Optional
from rest_framework.request import Request
from .navatara import NavataraCalculator
from .transit import TransitCalculator
from .astrological_subject import AstrologicalSubject
from .report import Report
from .dasha import DashaCalculator
import pytz
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
import time
from requests.exceptions import RequestException
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import tempfile
import logging
import uuid
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomerDetailsAPIView(APIView):
    ID_FILE_PATH = 'customer-data/last_id.json'

    def get_next_id(self):
        """
        Generate next sequential ID with improved error handling
        """
        # Ensure customer-data directory exists
        os.makedirs('customer-data', exist_ok=True)

        # If ID file doesn't exist or is invalid, start from 1
        try:
            if not os.path.exists(self.ID_FILE_PATH):
                current_id = 0
            else:
                with open(self.ID_FILE_PATH, 'r') as f:
                    content = f.read().strip()
                    current_id = int(content) if content else 0
        except (ValueError, IOError):
            current_id = 0

        # Increment and save the new ID
        next_id = current_id + 1
        
        with open(self.ID_FILE_PATH, 'w') as f:
            f.write(str(next_id))
        
        return str(next_id)

    def get_lat_long(self, place):
        """
        Geocode the given place and return latitude and longitude
        """
        geolocator = Nominatim(user_agent="astrology_app")
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            try:
                location = geolocator.geocode(place)
                if location:
                    return location.latitude, location.longitude
                else:
                    return None, None
            except (GeocoderTimedOut, GeocoderUnavailable):
                attempts += 1
        
        return None, None

    def round_decimal(self, value):
        """
        Round decimal values to 4 decimal places
        """
        return Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    def store_customer_details(self, customer_data):
        """
        Store customer details in a unique JSON file in the customer-data folder
        """
        # Ensure the customer-data directory exists
        customer_data_dir = 'customer-data'
        os.makedirs(customer_data_dir, exist_ok=True)
        
        # Always generate a new sequential ID 
        customer_id = self.get_next_id()
        customer_data['id'] = customer_id
        
        # Create file path with customer ID
        file_path = os.path.join(customer_data_dir, f"{customer_id}.json")
        
        # Write customer data to JSON file
        with open(file_path, 'w') as f:
            json.dump(customer_data, f, indent=4)
        
        return customer_data

    def post(self, request):
        try:
            # Extract customer details from request
            customer_data = request.data

            # If data is a string, try to parse it as JSON
            if isinstance(customer_data, str):
                try:
                    customer_data = json.loads(customer_data)
                except json.JSONDecodeError:
                    return Response(
                        {"error": "Invalid JSON data"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Create a copy to avoid modifying original
            customer_data = customer_data.copy()

            # If latitude and longitude are not provided, calculate them
            if not (customer_data.get('latitude') and customer_data.get('longitude')):
                # Calculate latitude and longitude
                birth_place = customer_data.get('birth_place')
                latitude, longitude = self.get_lat_long(birth_place)

                if latitude is None or longitude is None:
                    return Response(
                        {"error": "Unable to geocode the birth place"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Round latitude and longitude
                rounded_latitude = float(self.round_decimal(latitude))
                rounded_longitude = float(self.round_decimal(longitude))

                # Update customer data with rounded coordinates
                customer_data['latitude'] = str(rounded_latitude)
                customer_data['longitude'] = str(rounded_longitude)

            # Store customer details in JSON file
            stored_customer_data = self.store_customer_details(customer_data)

            # Return the full customer data including ID, latitude, and longitude
            return Response(stored_customer_data, status=status.HTTP_201_CREATED)

        except KeyError as e:
            return Response(
                {"error": f"Missing required field: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FetchCustomerDetailsAPIView(APIView):
    def get(self, request, customer_id):
        try:
            file_path = os.path.join(settings.BASE_DIR, 'customer-data', f'{customer_id}.json')
            if not os.path.exists(file_path):
                return Response(
                    {"error": "Customer not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            with open(file_path, 'r') as file:
                customer_data = json.load(file)

            if customer_data.get('id') != str(customer_id):
                return Response(
                    {"error": "Customer ID mismatch"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
            return Response(customer_data, status=status.HTTP_200_OK)
        
        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid JSON format"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except PermissionError:
            return Response(
                {"error": "Permission denied to read customer file"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
#------------------

class NavataraAPIView(APIView):
    def get(self, request, customer_id):
        try:
            if not customer_id:
                return Response({"error": "Customer ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            file_path = os.path.join(settings.BASE_DIR, 'customer-data', f'{customer_id}.json')
        
            if not os.path.exists(file_path):
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
            with open(file_path, 'r') as file:
                customer_data = json.load(file)
        
            if str(customer_data.get('id')) != str(customer_id):
                return Response({"error": "Customer ID mismatch"}, status=status.HTTP_400_BAD_REQUEST)
    
            calculator = NavataraCalculator(customer_data)
            result = calculator.calculate()
            
            return Response(result, status=status.HTTP_200_OK)
        
        except json.JSONDecodeError:
            return Response({"error": "Invalid customer data format"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except PermissionError:
            return Response({"error": "Permission denied to read customer file"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TransitAPIView(APIView):
    def get(self, request, customer_id):
        try:
            if not customer_id:
                return Response({"error": "Customer ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            file_path = os.path.join(settings.BASE_DIR, 'customer-data', f'{customer_id}.json')
        
            if not os.path.exists(file_path):
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
            with open(file_path, 'r') as file:
                customer_data = json.load(file)
            if str(customer_data.get('id')) != str(customer_id):
                return Response({"error": "Customer ID mismatch"}, status=status.HTTP_400_BAD_REQUEST)
            calculator = TransitCalculator(customer_data)
            result = calculator.calculate()
            
            return Response(result, status=status.HTTP_200_OK)
        
        except json.JSONDecodeError:
            return Response({"error": "Invalid customer data format"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except PermissionError:
            return Response({"error": "Permission denied to read customer file"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

#----------------------------------------------------Birth-Chart Data---------------------------------------------------------------------

class PlanetsAPIView(APIView):
    def get(self, request, customer_id):
        try:
            if not customer_id:
                return Response({"error": "Customer ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            file_path = os.path.join(settings.BASE_DIR, 'customer-data', f'{customer_id}.json')
            
            if not os.path.exists(file_path):
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
            
            with open(file_path, 'r') as file:
                customer_data = json.load(file)
            if str(customer_data.get('id')) != str(customer_id):
                return Response({"error": "Customer ID mismatch"}, status=status.HTTP_400_BAD_REQUEST)
            birth_date = customer_data['birth_date']
            birth_time = customer_data['birth_time']
            birth_place = customer_data['birth_place']

            year, month, day = map(int, birth_date.split('-'))
            hour, minute = map(int, birth_time.split(':'))

            place_parts = birth_place.split(',')
            city = place_parts[0].strip()
            country = place_parts[-1].strip() if len(place_parts) > 1 else ""

            subject = AstrologicalSubject(
                name=customer_data['name'],
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                city=city,
                nation=country,
                lng=float(customer_data['longitude']),
                lat=float(customer_data['latitude']),
                tz_str="Asia/Kolkata",
                zodiac_type="Sidereal",
                sidereal_mode="LAHIRI",
                houses_system_identifier='W',
                online=False
            )

            report = Report(subject)
            planets_data = report.get_planets_with_aspects()
           
            response_data = {
                "ascendant": {
                    "sign": subject.ascendant_sign,
                    "position": round(subject.ascendant_degree, 2)
                },
                "planets": planets_data
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({"error": "Invalid customer data format"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except PermissionError:
            return Response({"error": "Permission denied to read customer file"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DashaAPIView(APIView):
    def get(self, request, customer_id):
        try:
            if not customer_id:
                return Response({"error": "Customer ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            file_path = os.path.join(settings.BASE_DIR, 'customer-data', f'{customer_id}.json')
            
            if not os.path.exists(file_path):
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
            
            with open(file_path, 'r') as file:
                customer_data = json.load(file)

            if str(customer_data.get('id')) != str(customer_id):
                return Response({"error": "Customer ID mismatch"}, status=status.HTTP_400_BAD_REQUEST)

            calculator = DashaCalculator(customer_data)
            result = calculator.calculate()
            return Response(result, status=status.HTTP_200_OK)
        
        except json.JSONDecodeError:
            return Response({"error": "Invalid customer data format"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except PermissionError:
            return Response({"error": "Permission denied to read customer file"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GoodBadTimesAPIView(APIView):
    def get(self, request):
        LATITUDE = 28.6279        #delhi
        LONGITUDE = 77.3749
        TIMEZONE = 5.5

        API_KEY = settings.APIASTRO_API_KEY

        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist)

        payload = {
            "year": current_time.year,
            "month": current_time.month,
            "date": current_time.day,
            "hours": current_time.hour,
            "minutes": current_time.minute,
            "seconds": current_time.second,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "timezone": TIMEZONE,
            "config": {
                "observation_point": "geocentric",
                "ayanamsha": "lahiri"
            }
        }

        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post('https://json.apiastro.com/good-bad-times', json=payload, headers=headers)
            response.raise_for_status() 

            return Response(response.json(), status=status.HTTP_200_OK)

        except requests.RequestException as e:
            return Response({"error": f"API request failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BaseChartAPIView(APIView):
    chart_url = None  
    
    def get(self, request, customer_id):
        try:
          
            file_path = os.path.join(settings.BASE_DIR, 'customer-data', f'{customer_id}.json')
            
            if not os.path.exists(file_path):
                return Response(
                    {"error": "Customer not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            with open(file_path, 'r') as file:
                customer_data = json.load(file)
           
            if str(customer_data.get('id')) != str(customer_id):
                return Response(
                    {"error": "Customer ID mismatch"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            birth_date = datetime.strptime(customer_data['birth_date'], "%Y-%m-%d")
            birth_time = datetime.strptime(customer_data['birth_time'], "%H:%M")

            payload = {
                "year": birth_date.year,
                "month": birth_date.month,
                "date": birth_date.day,
                "hours": birth_time.hour,
                "minutes": birth_time.minute,
                "seconds": birth_time.second,
                "latitude": float(customer_data['latitude']),
                "longitude": float(customer_data['longitude']),
                "timezone": 5.5,
                "settings": {
                    "observation_point": "topocentric",
                    "ayanamsha": "lahiri"
                }
            }

            headers = {
                "x-api-key": settings.APIASTRO_API_KEY,
                "Content-Type": "application/json"
            }

            def make_request_with_retry(max_retries=3, delay=0.5):
                for attempt in range(max_retries):
                    try:
                        response = requests.post(self.chart_url, json=payload, headers=headers)
                        response.raise_for_status()
                        return response.json()
                    except RequestException as e:
                        if response.status_code == 429 and attempt < max_retries - 1:
                            time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        else:
                            return {"error": f"API request failed: {str(e)}"}
                return {"error": "Max retries reached"}

            chart_data = make_request_with_retry()
            return Response(chart_data, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid customer data format"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except PermissionError:
            return Response(
                {"error": "Permission denied to read customer file"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class D2ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d2-chart-info"

class D3ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d3-chart-info"

class D4ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d4-chart-info"

class D7ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d7-chart-info"

class NavamsaChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/navamsa-chart-info"

class D10ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d10-chart-info"

class D12ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d12-chart-info"

class D16ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d16-chart-info"

class D20ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d20-chart-info"

class D24ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d24-chart-info"

class D27ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d27-chart-info"

class D30ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d30-chart-info"

class D40ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d40-chart-info"

class D45ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d45-chart-info"

class D60ChartAPIView(BaseChartAPIView):
    chart_url = "https://json.apiastro.com/d60-chart-info"
