from typing import Optional, Dict, Any
from slack_sdk import WebClient

class ReactionManager:
    """
    Slack 'reactions' ailesi komutlarını yöneten sınıf.
    WebClient (bot veya user client) inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def add(self, channel: str, name: str, timestamp: str) -> Dict[str, Any]:
        """Adds a reaction to an item."""
        return self.client.reactions_add(channel=channel, name=name, timestamp=timestamp)

    def get(self, channel: Optional[str] = None, timestamp: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Gets reactions for an item."""
        return self.client.reactions_get(channel=channel, timestamp=timestamp, **kwargs)

    def list(self, user: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Lists reactions made by a user."""
        return self.client.reactions_list(user=user, **kwargs)

    def remove(self, name: str, channel: Optional[str] = None, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Removes a reaction from an item."""
        return self.client.reactions_remove(name=name, channel=channel, timestamp=timestamp)
