import swisseph as swe
from datetime import datetime, timedelta
import pytz
from timezonefinder import TimezoneFinder
from astropy.time import Time
from django.db import models


class TransitCalculator:
    def __init__(self, customer_data):
        
        self.customer = customer_data
        self.nakshatras = [
            "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
            "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", 
            "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", 
            "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", 
            "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
        ]
        self.ruling_planets = {
            "Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun", "Rohini": "Moon",
            "Mrigashira": "Mars", "Ardra": "Rahu", "Punarvasu": "Jupiter", "Pushya": "Saturn",
            "Ashlesha": "Mercury", "Magha": "Ketu", "Purva Phalguni": "Venus", 
            "Uttara Phalguni": "Sun", "Hasta": "Moon", "Chitra": "Mars", "Swati": "Rahu",
            "Vishakha": "Jupiter", "Anuradha": "Saturn", "Jyeshtha": "Mercury", 
            "Mula": "Ketu", "Purva Ashadha": "Venus", "Uttara Ashadha": "Sun",
            "Shravana": "Moon", "Dhanishta": "Mars", "Shatabhisha": "Rahu", 
            "Purva Bhadrapada": "Jupiter", "Uttara Bhadrapada": "Saturn", "Revati": "Mercury"
        }
        self.taras = [
            ("Janma", "Birth"), ("Sampat", "Wealth"), ("Vipat", "Danger"),
            ("Kshema", "Well-being"), ("Pratyak", "Obstacles"), ("Saadhana", "Achievement"),
            ("Naidhana", "Death"), ("Mitra", "Friend"), ("Parama Mitra", "Good friend")
        ]
        self.ayanamsha_mode = swe.SIDM_LAHIRI
        swe.set_sid_mode(self.ayanamsha_mode)
        self.zodiac_signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        
        self.exalted_signs = {
            "Sun": "Aries",
            "Moon": "Taurus",
            "Mars": "Capricorn",
            "Mercury": "Virgo",
            "Jupiter": "Cancer",
            "Venus": "Pisces",
            "Saturn": "Libra",
            "Rahu": "Taurus",
            "Ketu": "Scorpio"
        }
        
        self.debilitated_signs = {
            "Sun": "Libra",
            "Moon": "Scorpio",
            "Mars": "Cancer",
            "Mercury": "Pisces",
            "Jupiter": "Capricorn",
            "Venus": "Virgo",
            "Saturn": "Aries",
            "Rahu": "Scorpio",
            "Ketu": "Taurus"
        }
        
        self.own_signs = {
            "Sun": ["Leo"],
            "Moon": ["Cancer"],
            "Mars": ["Aries", "Scorpio"],
            "Mercury": ["Gemini", "Virgo"],
            "Jupiter": ["Sagittarius", "Pisces"],
            "Venus": ["Taurus", "Libra"],
            "Saturn": ["Capricorn", "Aquarius"],
            "Rahu": ["Aquarius"],
            "Ketu": ["Scorpio"]
        }

    def get_planetary_dignity(self, planet, zodiac_sign):
        if zodiac_sign == self.exalted_signs.get(planet):
            return "Exalted"
        elif zodiac_sign == self.debilitated_signs.get(planet):
            return "Debilitated"
        elif zodiac_sign in self.own_signs.get(planet, []):
            return "Own Sign"
        else:
            return "Normal"

    def get_local_timezone(self):
        tf = TimezoneFinder()
        return pytz.timezone(tf.timezone_at(
            lng=float(self.customer['longitude']), 
            lat=float(self.customer['latitude'])
        ))

    def get_birth_nakshatra(self):
        local_tz = self.get_local_timezone()
        birth_date = datetime.combine(
            datetime.strptime(self.customer['birth_date'], '%Y-%m-%d').date(), 
            datetime.strptime(self.customer['birth_time'], '%H:%M').time()
        )
        birth_date = local_tz.localize(birth_date)
        utc_birth_date = birth_date.astimezone(pytz.UTC)
        
        jd = swe.julday(utc_birth_date.year, utc_birth_date.month, utc_birth_date.day, 
                        utc_birth_date.hour + utc_birth_date.minute/60.0 + utc_birth_date.second/3600.0)
        
        positions = self.get_planet_positions(jd)
        return positions['Moon']['nakshatra']
    
    def get_zodiac_sign(self, longitude):
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                 "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        return signs[int(longitude / 30)]

    def get_nakshatra_progress(self, longitude):
        nakshatra_span = 360 / 27 
        return (longitude % nakshatra_span) 

    def sidereal_longitude(self, jd, longitude):
        ayanamsha = swe.get_ayanamsa(jd)
        return (longitude - ayanamsha) % 360

    def get_nakshatra(self, longitude):
        nakshatra_index = int(longitude * 27 / 360)
        return self.nakshatras[nakshatra_index]

    def get_planet_positions(self, jd):
        positions = {}
        planet_names = {
            swe.SUN: "Sun", swe.MOON: "Moon", swe.MERCURY: "Mercury",
            swe.VENUS: "Venus", swe.MARS: "Mars", swe.JUPITER: "Jupiter",
            swe.SATURN: "Saturn"
        }
        
        for planet_id, planet_name in planet_names.items():
            result = swe.calc_ut(jd, planet_id)
            lon = result[0][0]  
            sid_lon = self.sidereal_longitude(jd, lon)
            nakshatra = self.get_nakshatra(sid_lon)
            positions[planet_name] = {
                'longitude': round(sid_lon, 2),
                'nakshatra': nakshatra,
            }
        
        rahu_ketu = self.calculate_rahu_ketu(jd, positions["Moon"]['longitude'], positions["Sun"]['longitude'])
        positions.update(rahu_ketu)
        
        return positions

    def calculate_rahu_ketu(self, jd, moon_longitude, sun_longitude):
        rahu_tropical = (sun_longitude + 180) % 360
        rahu_sidereal = self.sidereal_longitude(jd, rahu_tropical)
        ketu_sidereal = (rahu_sidereal + 180) % 360
        
        return {
            'Rahu': {
                'longitude': round(rahu_sidereal, 2),
                'nakshatra': self.get_nakshatra(rahu_sidereal),
            },
            'Ketu': {
                'longitude': round(ketu_sidereal, 2),
                'nakshatra': self.get_nakshatra(ketu_sidereal),
            }
        }

    def find_nakshatra_boundaries(self, planet, start_jd, nakshatra):
        local_tz = self.get_local_timezone()
        jd = start_jd
        while self.get_planet_positions(jd)[planet]['nakshatra'] == nakshatra:
            jd -= 1/24 
        start_time = Time(jd + 1/24, format='jd').datetime
        start_time = pytz.utc.localize(start_time).astimezone(local_tz)
        jd = start_jd
        while self.get_planet_positions(jd)[planet]['nakshatra'] == nakshatra:
            jd += 1/24  
        end_time = Time(jd - 1/24, format='jd').datetime
        end_time = pytz.utc.localize(end_time).astimezone(local_tz)
        return start_time, end_time
    
    def get_planet_tara(self, planet_nakshatra, birth_nakshatra):
        start_index = self.nakshatras.index(birth_nakshatra)
        planet_index = self.nakshatras.index(planet_nakshatra)
        tara_index = (planet_index - start_index) % 9
        return self.taras[tara_index]

    def calculate_transit_table(self):
        local_tz = self.get_local_timezone()
        birth_nakshatra = self.get_birth_nakshatra()
        
        current_time = Time.now()
        jd = current_time.jd
        
        date = current_time.datetime
        date = pytz.utc.localize(date).astimezone(local_tz)
        
        positions = self.get_planet_positions(jd)
        
        transit_data = []
        
        for planet, data in positions.items():
            tara, meaning = self.get_planet_tara(data['nakshatra'], birth_nakshatra)
            planet_tara = f"{tara} ({meaning})" if tara else "Couldn't determine"
            
            start_time, end_time = self.find_nakshatra_boundaries(planet, jd, data['nakshatra'])
            zodiac_sign = self.get_zodiac_sign(data['longitude'])
            nakshatra_progress = self.get_nakshatra_progress(data['longitude'])
            dignity = self.get_planetary_dignity(planet, zodiac_sign)
            
            transit_data.append({
                "Planet": planet,  
                "Longitude": f"{data['longitude']:.2f}",
                "Nakshatra": data['nakshatra'],
                "Planet's Tara": planet_tara,
                "Nakshatra Start": start_time.strftime('%Y-%m-%d %H:%M'),
                "Nakshatra End": end_time.strftime('%Y-%m-%d %H:%M'),
                "Zodiac Sign": zodiac_sign,
                "Nakshatra Degree": f"{nakshatra_progress:.2f}"   
            })
        
        return transit_data
 
#----------------------------------------------------------Planetary Interpretations----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 
    def calculate(self):
        transit_table = self.calculate_transit_table()
        return {
            "transit_table": transit_table
        }
