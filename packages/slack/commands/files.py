from typing import Optional, List, Dict, Any
from slack_sdk import WebClient

class FileManager:
    """
    Slack 'files' ailesi komutlarını yöneten sınıf.
    WebClient (bot veya user client) inject edilmiştir.
    """

    def __init__(self, client: WebClient):
        self.client = client

    def delete_comment(self, file: str, id: str, **kwargs) -> Dict[str, Any]:
        """Deletes an existing comment on a file."""
        return self.client.files_comments_delete(file=file, id=id, **kwargs)

    def complete_upload_external(self, files: List[Dict], channel_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Finishes an upload started with files.getUploadURLExternal."""
        return self.client.files_completeUploadExternal(files=files, channel_id=channel_id, **kwargs)

    def delete(self, file: str, **kwargs) -> Dict[str, Any]:
        """Deletes a file."""
        return self.client.files_delete(file=file, **kwargs)

    def get_upload_url_external(self, filename: str, length: int, **kwargs) -> Dict[str, Any]:
        """Gets a URL for an edge external file upload."""
        return self.client.files_getUploadURLExternal(filename=filename, length=length, **kwargs)

    def info(self, file: str, **kwargs) -> Dict[str, Any]:
        """Gets information about a file."""
        return self.client.files_info(file=file, **kwargs)

    def list(self, **kwargs) -> Dict[str, Any]:
        """List files for a team, in a channel, or from a user."""
        return self.client.files_list(**kwargs)

    # --- Remote Files ---

    def remote_add(self, external_id: str, external_url: str, title: str, **kwargs) -> Dict[str, Any]:
        """Adds a file from a remote service."""
        return self.client.files_remote_add(external_id=external_id, external_url=external_url, title=title, **kwargs)

    def remote_info(self, external_id: Optional[str] = None, file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Retrieve information about a remote file."""
        return self.client.files_remote_info(external_id=external_id, file=file, **kwargs)

    def remote_list(self, **kwargs) -> Dict[str, Any]:
        """Retrieve information about remote files."""
        return self.client.files_remote_list(**kwargs)

    def remote_remove(self, external_id: Optional[str] = None, file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Remove a remote file."""
        return self.client.files_remote_remove(external_id=external_id, file=file, **kwargs)

    def remote_share(self, channels: str, external_id: Optional[str] = None, file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Share a remote file into a channel."""
        return self.client.files_remote_share(channels=channels, external_id=external_id, file=file, **kwargs)

    def remote_update(self, external_id: Optional[str] = None, file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Updates an existing remote file."""
        return self.client.files_remote_update(external_id=external_id, file=file, **kwargs)

    # --- Sharing ---

    def revoke_public_url(self, file: str, **kwargs) -> Dict[str, Any]:
        """Revokes public/external sharing access for a file."""
        return self.client.files_revokePublicURL(file=file, **kwargs)

    def shared_public_url(self, file: str, **kwargs) -> Dict[str, Any]:
        """Enables a file for public/external sharing."""
        return self.client.files_sharedPublicURL(file=file, **kwargs)

    def upload(self, file: Optional[str] = None, content: Optional[str] = None, channels: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Uploads or creates a file."""
        return self.client.files_upload(file=file, content=content, channels=channels, **kwargs)
