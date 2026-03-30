from typing import Optional, Dict, Any
from slack_sdk import WebClient

class PinManager:
    """
    Slack 'pins' ailesi komutlarını yöneten sınıf.
    WebClient inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def add(self, channel: str, timestamp: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Pins an item (message) to a channel."""
        return self.client.pins_add(channel=channel, timestamp=timestamp, **kwargs)

    def list(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Lists items pinned to a channel."""
        return self.client.pins_list(channel=channel, **kwargs)

    def remove(self, channel: str, timestamp: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Unpins an item (message) from a channel."""
        return self.client.pins_remove(channel=channel, timestamp=timestamp, **kwargs)
