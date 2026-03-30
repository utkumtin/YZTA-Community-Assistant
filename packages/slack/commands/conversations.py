from typing import Optional, List, Dict, Any
from slack_sdk import WebClient

class ConversationManager:
    """
    Slack 'conversations' ailesi komutlarını yöneten sınıf.
    WebClient (bot veya user client) inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def accept_shared_invite(self, invite_id: str, channel_name: str, **kwargs) -> Dict[str, Any]:
        """Accepts an invitation to a Slack Connect channel."""
        return self.client.conversations_acceptSharedInvite(invite_id=invite_id, channel_name=channel_name, **kwargs)

    def approve_shared_invite(self, invite_id: str, **kwargs) -> Dict[str, Any]:
        """Approves an invitation to a Slack Connect channel."""
        return self.client.conversations_approveSharedInvite(invite_id=invite_id, **kwargs)

    def archive(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Archives a conversation."""
        return self.client.conversations_archive(channel=channel, **kwargs)

    def create_canvas(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Create a channel canvas for a channel."""
        return self.client.conversations_canvases_create(channel=channel, **kwargs)

    def close(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Closes a direct message or multi-person direct message."""
        return self.client.conversations_close(channel=channel, **kwargs)

    def create(self, name: str, is_private: bool = False, **kwargs) -> Dict[str, Any]:
        """Initiates a public or private channel-based conversation."""
        return self.client.conversations_create(name=name, is_private=is_private, **kwargs)

    def decline_shared_invite(self, invite_id: str, **kwargs) -> Dict[str, Any]:
        """Declines a Slack Connect channel invite."""
        return self.client.conversations_declineSharedInvite(invite_id=invite_id, **kwargs)

    def set_external_invite_permissions(self, channel: str, action: str, target_team: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Upgrade or downgrade Slack Connect channel permissions."""
        return self.client.conversations_externalInvitePermissions_set(channel=channel, action=action, target_team=target_team, **kwargs)

    def history(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Fetches a conversation's history of messages and events."""
        return self.client.conversations_history(channel=channel, **kwargs)

    def info(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Retrieve information about a conversation."""
        return self.client.conversations_info(channel=channel, **kwargs)

    def invite(self, channel: str, users: List[str], **kwargs) -> Dict[str, Any]:
        """Invites users to a channel."""
        return self.client.conversations_invite(channel=channel, users=users, **kwargs)

    def invite_shared(self, channel: str, emails: Optional[List[str]] = None, user_ids: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Sends an invitation to a Slack Connect channel."""
        return self.client.conversations_inviteShared(channel=channel, emails=emails, user_ids=user_ids, **kwargs)

    def join(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Joins an existing conversation."""
        return self.client.conversations_join(channel=channel, **kwargs)

    def kick(self, channel: str, user: str, **kwargs) -> Dict[str, Any]:
        """Removes a user from a conversation."""
        return self.client.conversations_kick(channel=channel, user=user, **kwargs)

    def leave(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Leaves a conversation."""
        return self.client.conversations_leave(channel=channel, **kwargs)

    def list(self, **kwargs) -> Dict[str, Any]:
        """Lists all channels in a Slack team."""
        return self.client.conversations_list(**kwargs)

    def list_connect_invites(self, **kwargs) -> Dict[str, Any]:
        """Lists shared channel invites."""
        return self.client.conversations_listConnectInvites(**kwargs)

    def mark(self, channel: str, ts: str, **kwargs) -> Dict[str, Any]:
        """Sets the read cursor in a channel."""
        return self.client.conversations_mark(channel=channel, ts=ts, **kwargs)

    def members(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Retrieve members of a conversation."""
        return self.client.conversations_members(channel=channel, **kwargs)

    def open(self, users: Optional[List[str]] = None, channel: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Opens or resumes a direct message or multi-person direct message."""
        return self.client.conversations_open(users=users, channel=channel, **kwargs)

    def rename(self, channel: str, name: str, **kwargs) -> Dict[str, Any]:
        """Renames a conversation."""
        return self.client.conversations_rename(channel=channel, name=name, **kwargs)

    def replies(self, channel: str, ts: str, **kwargs) -> Dict[str, Any]:
        """Retrieve a thread of messages posted to a conversation."""
        return self.client.conversations_replies(channel=channel, ts=ts, **kwargs)

    def approve_request_shared_invite(self, invite_id: str, **kwargs) -> Dict[str, Any]:
        """Approves a request to add an external user to a channel."""
        return self.client.conversations_requestSharedInvite_approve(invite_id=invite_id, **kwargs)

    def deny_request_shared_invite(self, invite_id: str, **kwargs) -> Dict[str, Any]:
        """Denies a request to invite an external user to a channel."""
        return self.client.conversations_requestSharedInvite_deny(invite_id=invite_id, **kwargs)

    def list_request_shared_invites(self, **kwargs) -> Dict[str, Any]:
        """Lists requests to add external users to channels."""
        return self.client.conversations_requestSharedInvite_list(**kwargs)

    def set_purpose(self, channel: str, purpose: str, **kwargs) -> Dict[str, Any]:
        """Sets the channel description."""
        return self.client.conversations_setPurpose(channel=channel, purpose=purpose, **kwargs)

    def set_topic(self, channel: str, topic: str, **kwargs) -> Dict[str, Any]:
        """Sets the topic for a conversation."""
        return self.client.conversations_setTopic(channel=channel, topic=topic, **kwargs)

    def unarchive(self, channel: str, **kwargs) -> Dict[str, Any]:
        """Reverses conversation archival."""
        return self.client.conversations_unarchive(channel=channel, **kwargs)
