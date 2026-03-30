from typing import Optional, List, Dict, Any, Union
from slack_sdk import WebClient


class ChatManager:
    """
    Slack 'chat' ailesi komutlarını (mesajlaşma, planlama, streaming) yöneten sınıf.
    WebClient (bot_client) inject edilmiştir.
    """

    def __init__(self, bot_client: WebClient):
        self.client = bot_client

    def post_message(self, channel: str, text: str, blocks: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
        """Sends a message (chat.postMessage)."""
        return self.client.chat_postMessage(channel=channel, text=text, blocks=blocks, **kwargs)

    def post_ephemeral(self, channel: str, user: str, text: str, blocks: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
        """Sends an ephemeral message (chat.postEphemeral)."""
        return self.client.chat_postEphemeral(channel=channel, user=user, text=text, blocks=blocks, **kwargs)

    def update(self, channel: str, ts: str, text: str, blocks: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
        """Updates a message (chat.update)."""
        return self.client.chat_update(channel=channel, ts=ts, text=text, blocks=blocks, **kwargs)

    def delete(self, channel: str, ts: str, **kwargs) -> Dict[str, Any]:
        """Deletes a message (chat.delete)."""
        return self.client.chat_delete(channel=channel, ts=ts, **kwargs)

    def get_permalink(self, channel: str, message_ts: str) -> Dict[str, Any]:
        """Retrieve a permalink URL (chat.getPermalink)."""
        return self.client.chat_getPermalink(channel=channel, message_ts=message_ts)

    def me_message(self, channel: str, text: str) -> Dict[str, Any]:
        """Share a me message (chat.meMessage)."""
        return self.client.chat_meMessage(channel=channel, text=text)

    def schedule_message(self, channel: str, post_at: Union[int, str], text: str, **kwargs) -> Dict[str, Any]:
        """Schedules a message (chat.scheduleMessage)."""
        return self.client.chat_scheduleMessage(channel=channel, post_at=post_at, text=text, **kwargs)

    def delete_scheduled_message(self, channel: str, scheduled_message_id: str) -> Dict[str, Any]:
        """Deletes a scheduled message (chat.deleteScheduledMessage)."""
        return self.client.chat_deleteScheduledMessage(channel=channel, scheduled_message_id=scheduled_message_id)

    def list_scheduled_messages(self, **kwargs) -> Dict[str, Any]:
        """Lists scheduled messages (chat.scheduledMessages.list)."""
        return self.client.chat_scheduledMessages_list(**kwargs)

    def unfurl(self, channel: str, ts: str, unfurls: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Provide custom unfurl behavior (chat.unfurl)."""
        return self.client.chat_unfurl(channel=channel, ts=ts, unfurls=unfurls, **kwargs)

    # --- Streaming ---

    def start_stream(self, channel: str, text: str, **kwargs) -> Dict[str, Any]:
        """Starts a streaming conversation (chat.startStream)."""
        return self.client.chat_startStream(channel=channel, text=text, **kwargs)

    def append_stream(self, channel: str, stream_id: str, text: str, **kwargs) -> Dict[str, Any]:
        """Appends text to a stream (chat.appendStream)."""
        return self.client.chat_appendStream(channel=channel, stream_id=stream_id, text=text, **kwargs)

    def stop_stream(self, channel: str, stream_id: str, **kwargs) -> Dict[str, Any]:
        """Stops a streaming conversation (chat.stopStream)."""
        return self.client.chat_stopStream(channel=channel, stream_id=stream_id, **kwargs)
