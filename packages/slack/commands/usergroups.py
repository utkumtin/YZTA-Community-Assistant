from typing import Optional, List, Dict, Any
from slack_sdk import WebClient

class UserGroupManager:
    """
    Slack 'usergroups' ailesi komutlarını yöneten sınıf.
    WebClient (bot veya user client) inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def create(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a User Group."""
        return self.client.usergroups_create(name=name, **kwargs)

    def disable(self, usergroup: str, **kwargs) -> Dict[str, Any]:
        """Disable an existing User Group."""
        return self.client.usergroups_disable(usergroup=usergroup, **kwargs)

    def enable(self, usergroup: str, **kwargs) -> Dict[str, Any]:
        """Enable a User Group."""
        return self.client.usergroups_enable(usergroup=usergroup, **kwargs)

    def list(self, **kwargs) -> Dict[str, Any]:
        """List all User Groups for a team."""
        return self.client.usergroups_list(**kwargs)

    def update(self, usergroup: str, **kwargs) -> Dict[str, Any]:
        """Update an existing User Group."""
        return self.client.usergroups_update(usergroup=usergroup, **kwargs)

    def list_users(self, usergroup: str, **kwargs) -> Dict[str, Any]:
        """List all users in a User Group."""
        return self.client.usergroups_users_list(usergroup=usergroup, **kwargs)

    def update_users(self, usergroup: str, users: List[str], **kwargs) -> Dict[str, Any]:
        """Update the list of users for a user group."""
        return self.client.usergroups_users_update(usergroup=usergroup, users=users, **kwargs)
