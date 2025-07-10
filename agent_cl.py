import os
import requests
from openai import OpenAI
import json
from dotenv import load_dotenv
load_dotenv()

# ---- Configuration ----
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# ---- Input validation ----
def validate_city_input(city):
    """Validate and sanitize city input"""
    if not city or not city.strip():
        raise ValueError("Název města nesmí být prázdný")

    # Basic sanitization - remove special characters that could cause issues
    city = city.strip()
    if len(city) > 100:  # Reasonable length limit
        raise ValueError("Název města je příliš dlouhý")

    return city


# ---- Weather API function ----
def get_weather(city):
    """Get current weather data with improved error handling"""
    if not OPENWEATHERMAP_API_KEY:
        raise Exception("OPENWEATHERMAP_API_KEY není nastaven")

    city = validate_city_input(city)

    url = (
        f"https://api.openweathermap.org/data/2.5/weather?q={city}"
        f"&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=cz"
    )

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            raise Exception(f"Město '{city}' nebylo nalezeno")
        elif response.status_code == 401:
            raise Exception("Neplatný API klíč pro OpenWeatherMap")
        elif response.status_code != 200:
            raise Exception(f"Chyba při získávání počasí: {response.status_code}")

        return response.json()

    except requests.exceptions.Timeout:
        raise Exception("Timeout při dotazu na počasí")
    except requests.exceptions.ConnectionError:
        raise Exception("Chyba připojení k API počasí")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Chyba při dotazu na počasí: {str(e)}")


# ---- Enhanced prompt building ----
def build_prompt(weather_data):
    """Build comprehensive prompt with additional weather factors"""
    try:
        temp = weather_data["main"]["temp"]
        feels_like = weather_data["main"]["feels_like"]
        desc = weather_data["weather"][0]["description"]
        wind = weather_data["wind"]["speed"]
        humidity = weather_data["main"]["humidity"]

        # Optional fields that might not be present
        visibility = weather_data.get("visibility", "N/A")
        pressure = weather_data["main"].get("pressure", "N/A")

        # Check for precipitation
        rain = weather_data.get("rain", {}).get("1h", 0)
        snow = weather_data.get("snow", {}).get("1h", 0)

        weather_summary = (
            f"Teplota: {temp}°C (pocitová {feels_like}°C), "
            f"Počasí: {desc}, "
            f"Vítr: {wind} m/s, "
            f"Vlhkost: {humidity}%"
        )

        if rain > 0:
            weather_summary += f", Déšť: {rain}mm/h"
        if snow > 0:
            weather_summary += f", Sníh: {snow}mm/h"

        prompt = (
            f"Na základě následujícího počasí poraď, co si mám dnes obléct: {weather_summary}.\n"
            "Vezmi v úvahu teplotu, pocitovou teplotu, srážky, vítr a vlhkost. "
            "Buď stručný a praktický. Doporuč konkrétní kusy oblečení."
        )

        return prompt

    except KeyError as e:
        raise Exception(f"Chybí očekávaná data v odpovědi API: {str(e)}")


# ---- OpenAI API function ----
def ask_gpt(prompt):
    """Query OpenAI API with improved error handling"""
    if not client:
        raise Exception("OpenAI API klíč není nastaven")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Correct model name
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,  # Limit response length
            timeout=30
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        raise Exception(f"Chyba při dotazu na OpenAI: {str(e)}")


# ---- Main CLI function ----
def main():
    """Main application function with improved error handling"""
    print("👕 AI Obleč-se Agent\n")

    try:
        city = input("Zadej město: ").strip()

        if not city:
            print("⚠️  Chyba: Musíte zadat název města")
            return

        print(f"🌤️  Získávám počasí pro {city}...")
        weather_data = get_weather(city)

        print("🤖 Generuji doporučení...")
        prompt = build_prompt(weather_data)
        recommendation = ask_gpt(prompt)

        print(f"\n🧥 Doporučení pro {weather_data['name']}:")
        print(recommendation)

        # Optional: Show basic weather info
        temp = weather_data["main"]["temp"]
        desc = weather_data["weather"][0]["description"]
        print(f"\n📊 Aktuální počasí: {temp}°C, {desc}")

    except KeyboardInterrupt:
        print("\n👋 Ukončeno uživatelem")
    except Exception as e:
        print(f"⚠️  Chyba: {e}")


if __name__ == "__main__":
    main()