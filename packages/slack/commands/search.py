from typing import Optional, Dict, Any
from slack_sdk import WebClient

class SearchManager:
    """
    Slack 'search' ailesi komutlarını yöneten sınıf.
    WebClient inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def all(self, query: str, **kwargs) -> Dict[str, Any]:
        """Searches for messages and files of a team."""
        return self.client.search_all(query=query, **kwargs)

    def files(self, query: str, **kwargs) -> Dict[str, Any]:
        """Searches for files matching a query."""
        return self.client.search_files(query=query, **kwargs)

    def messages(self, query: str, **kwargs) -> Dict[str, Any]:
        """Searches for messages matching a query."""
        return self.client.search_messages(query=query, **kwargs)
