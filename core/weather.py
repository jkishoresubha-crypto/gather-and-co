"""Server-side OpenWeather client with timeouts, validation and caching."""
import logging
import re

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("gather.weather")

API_URL = "https://api.openweathermap.org/data/2.5/weather"
CITY_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ .,'\-]{2,60}$")


class WeatherResult(dict):
    """Plain dict with `ok` and either weather fields or a friendly `message`."""


def validate_city(city):
    city = (city or "").strip()
    if not CITY_PATTERN.match(city):
        return None
    return city


def unavailable(message):
    return WeatherResult(ok=False, message=message)


def get_weather(city=None):
    city = validate_city(city or settings.DEFAULT_WEATHER_CITY)
    if city is None:
        return unavailable("Please enter a valid city name (letters, spaces and hyphens only).")

    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return unavailable("Live weather is temporarily unavailable (the weather service is not configured).")

    cache_key = "weather:" + city.lower().replace(" ", "_")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            API_URL,
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=(settings.WEATHER_CONNECT_TIMEOUT, settings.WEATHER_READ_TIMEOUT),
        )
    except requests.Timeout:
        logger.warning("OpenWeather request timed out city=%s", city)
        return unavailable("Live weather is temporarily unavailable (the weather service timed out).")
    except requests.RequestException as exc:
        logger.warning("OpenWeather request failed city=%s error=%s", city, type(exc).__name__)
        return unavailable("Live weather is temporarily unavailable. Please try again later.")

    if response.status_code == 404:
        return unavailable(f"We couldn't find weather for “{city}”. Check the spelling and try again.")
    if response.status_code == 429:
        logger.warning("OpenWeather rate limit reached")
        return unavailable("Live weather is busy right now (rate limit reached). Please try again shortly.")
    if response.status_code in (401, 403):
        logger.error("OpenWeather rejected the API key status=%s", response.status_code)
        return unavailable("Live weather is temporarily unavailable.")
    if response.status_code != 200:
        logger.warning("OpenWeather returned status=%s", response.status_code)
        return unavailable("Live weather is temporarily unavailable. Please try again later.")

    try:
        data = response.json()
        result = WeatherResult(
            ok=True,
            city=str(data["name"]),
            country=str(data.get("sys", {}).get("country", "")),
            temp=round(float(data["main"]["temp"])),
            feels_like=round(float(data["main"]["feels_like"])),
            humidity=int(data["main"]["humidity"]),
            wind=round(float(data.get("wind", {}).get("speed", 0)), 1),
            description=str(data["weather"][0]["description"]).capitalize(),
            icon=re.sub(r"[^0-9a-z]", "", str(data["weather"][0]["icon"]))[:4],
        )
    except (ValueError, KeyError, IndexError, TypeError):
        logger.warning("OpenWeather returned a malformed response")
        return unavailable("Live weather is temporarily unavailable (unexpected response).")

    cache.set(cache_key, result, settings.WEATHER_CACHE_SECONDS)
    return result
