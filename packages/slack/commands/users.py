from typing import Optional, Dict, Any, List
from slack_sdk import WebClient

class UserManager:
    """
    Slack 'users' ailesi komutlarını yöneten sınıf.
    WebClient (bot veya user client) inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def conversations(self, **kwargs) -> Dict[str, Any]:
        """List conversations the calling user is a member of."""
        return self.client.users_conversations(**kwargs)

    def delete_photo(self) -> Dict[str, Any]:
        """Delete the user profile photo."""
        return self.client.users_deletePhoto()

    def discoverable_contacts_lookup(self, email: str, **kwargs) -> Dict[str, Any]:
        """Look up an email address to see if someone is discoverable on Slack."""
        return self.client.users_discoverableContacts_lookup(email=email, **kwargs)

    def get_presence(self, user: str) -> Dict[str, Any]:
        """Gets user presence information."""
        return self.client.users_getPresence(user=user)

    def identity(self) -> Dict[str, Any]:
        """Get a user's identity."""
        return self.client.users_identity()

    def info(self, user: str, **kwargs) -> Dict[str, Any]:
        """Gets information about a user."""
        return self.client.users_info(user=user, **kwargs)

    def list(self, **kwargs) -> Dict[str, Any]:
        """Lists all users in a Slack team."""
        return self.client.users_list(**kwargs)

    def lookup_by_email(self, email: str) -> Dict[str, Any]:
        """Find a user with an email address."""
        return self.client.users_lookupByEmail(email=email)

    def profile_get(self, user: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Retrieve a user's profile information."""
        return self.client.users_profile_get(user=user, **kwargs)

    def profile_set(self, user: Optional[str] = None, profile: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Set a user's profile information."""
        return self.client.users_profile_set(user=user, profile=profile, **kwargs)

    def set_active(self) -> Dict[str, Any]:
        """Marked a user as active. (Deprecated but kept for compatibility)"""
        return self.client.users_setActive()

    def set_photo(self, image: str, **kwargs) -> Dict[str, Any]:
        """Set the user profile photo."""
        return self.client.users_setPhoto(image=image, **kwargs)

    def set_presence(self, presence: str) -> Dict[str, Any]:
        """Manually sets user presence."""
        return self.client.users_setPresence(presence=presence)
