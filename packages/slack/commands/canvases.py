from typing import Optional, List, Dict, Any
from slack_sdk import WebClient

class CanvasManager:
    """
    Slack 'canvases' ailesi komutlarını yöneten sınıf.
    WebClient (bot veya user client) inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def create(self, title: str, content: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Create canvas for a user."""
        return self.client.canvases_create(title=title, content=content, **kwargs)

    def delete(self, canvas_id: str, **kwargs) -> Dict[str, Any]:
        """Deletes a canvas."""
        return self.client.canvases_delete(canvas_id=canvas_id, **kwargs)

    def edit(self, canvas_id: str, changes: List[Dict], **kwargs) -> Dict[str, Any]:
        """Update an existing canvas."""
        return self.client.canvases_edit(canvas_id=canvas_id, changes=changes, **kwargs)

    def access_delete(self, canvas_id: str, user_ids: Optional[List[str]] = None, channel_ids: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Remove access to a canvas for specified entities."""
        return self.client.canvases_access_delete(canvas_id=canvas_id, user_ids=user_ids, channel_ids=channel_ids, **kwargs)

    def access_set(self, canvas_id: str, access_level: str, user_ids: Optional[List[str]] = None, channel_ids: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Sets the access level to a canvas for specified entities."""
        return self.client.canvases_access_set(canvas_id=canvas_id, access_level=access_level, user_ids=user_ids, channel_ids=channel_ids, **kwargs)

    def sections_lookup(self, canvas_id: str, criteria: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Find sections matching the provided criteria."""
        return self.client.canvases_sections_lookup(canvas_id=canvas_id, criteria=criteria, **kwargs)
