import os
import webbrowser
import pywhatkit
import pyautogui

class MediaCommands:
    @staticmethod
    def play_on_youtube(query):
        """Plays the most relevant video on YouTube."""
        if not query:
            return "What should I play on YouTube?"
        try:
            print(f"[MEDIA] YouTube Play: {query}")
            pywhatkit.playonyt(query)
            return f"Playing {query} on YouTube."
        except Exception as e:
            print(f"[ERR] YouTube Play: {e}")
            # Fallback to search
            url = f"https://www.youtube.com/results?search_query={query}"
            webbrowser.open(url)
            return f"Opening YouTube search for {query}."

    @staticmethod
    def play_on_spotify(query):
        """Searches and plays a song on Spotify."""
        if not query:
            # Just open Spotify
            os.system("start spotify")
            return "Opening Spotify."
        
        try:
            print(f"[MEDIA] Spotify Search: {query}")
            # Use Spotify URI search
            # Note: This opens the search page in the app
            search_url = f"spotify:search:{query}"
            os.startfile(search_url)
            
            # Auto-play logic is tricky without API, but we can try to press Enter
            # wait a bit for app to open
            import threading
            import time
            def auto_play():
                time.sleep(5)
                pyautogui.press('enter')
            
            threading.Thread(target=auto_play, daemon=True).start()
            
            return f"Searching for {query} on Spotify."
        except Exception as e:
            print(f"[ERR] Spotify: {e}")
            # Web fallback
            url = f"https://open.spotify.com/search/{query}"
            webbrowser.open(url)
            return f"Opening Spotify search for {query}."

    @staticmethod
    def scroll(direction, amount=3):
        """Scrolls the screen up or down."""
        # amount 1-10 scale
        clicks = amount * 300
        if "up" in direction.lower():
            pyautogui.scroll(clicks)
            return "Scrolling up."
        else:
            pyautogui.scroll(-clicks)
            return "Scrolling down."
