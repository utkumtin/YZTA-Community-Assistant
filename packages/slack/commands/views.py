from typing import Optional, Dict, Any, Union
from slack_sdk import WebClient

class ViewManager:
    """
    Slack 'views' (Modals & Home Tab) ailesi komutlarını yöneten sınıf.
    Interaktif uygulamalar için kritiktir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def open(self, trigger_id: str, view: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Open a view for a user (Modal)."""
        return self.client.views_open(trigger_id=trigger_id, view=view, **kwargs)

    def publish(self, user_id: str, view: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Publish a static view for a user (Home Tab)."""
        return self.client.views_publish(user_id=user_id, view=view, **kwargs)

    def push(self, trigger_id: str, view: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Push a view onto the stack of a dynamic modal."""
        return self.client.views_push(trigger_id=trigger_id, view=view, **kwargs)

    def update(self, view: Dict[str, Any], view_id: Optional[str] = None, external_id: Optional[str] = None, hash: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Update an existing view."""
        return self.client.views_update(view=view, view_id=view_id, external_id=external_id, hash=hash, **kwargs)
