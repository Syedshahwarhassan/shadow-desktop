import webbrowser

class WebCommands:
    @staticmethod
    def search_google(query):
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        return f"Searching Google for {query}."

    @staticmethod
    def play_youtube(query):
        url = f"https://www.youtube.com/results?search_query={query}"
        webbrowser.open(url)
        return f"Searching YouTube for {query}."

    @staticmethod
    def open_website(url):
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opening {url}."
