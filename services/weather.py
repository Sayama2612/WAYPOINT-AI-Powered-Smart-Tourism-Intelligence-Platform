import os
import requests

API_KEY = os.getenv('OPENWEATHER_API_KEY')

def get_weather(lat, lon):
    if not API_KEY:
        return None
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        return r.json()
    return None
