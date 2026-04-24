import requests
import pyjokes
import yfinance as yf
from config_manager import config_manager

class ProductivityCommands:
    @staticmethod
    def get_weather(city):
        api_key = config_manager.get("api_keys.openweathermap")
        if not api_key:
            return "Weather API key not configured."
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            res = requests.get(url).json()
            temp = res['main']['temp']
            desc = res['weather'][0]['description']
            return f"The weather in {city} is {desc} with a temperature of {temp}°C."
        except:
            return f"Could not get weather for {city}."

    @staticmethod
    def tell_joke():
        return pyjokes.get_joke()

    @staticmethod
    def stock_price(symbol):
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.history(period="1d")['Close'].iloc[-1]
            return f"The current price of {symbol} is ${price:.2f}."
        except:
            return f"Could not find stock data for {symbol}."

    @staticmethod
    def get_quote():
        try:
            res = requests.get("https://api.quotable.io/random").json()
            return f"{res['content']} - {res['author']}"
        except:
            return "Could not fetch a quote."
