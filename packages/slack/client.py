from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from packages.settings import get_settings


class SlackClientManager():
    settings = get_settings()

    _app: App | None = None    
    _bot_client: WebClient | None = None
    _user_client: WebClient | None = None
    _socket_handler: SocketModeHandler | None = None

    @property
    def app(self) -> App:
        if self._app is None:
            self._app = App(token=self.settings.slack_bot_token)
        return self._app

    @property
    def bot_client(self) -> WebClient:
        if self._bot_client is None:
            self._bot_client = WebClient(token=self.settings.slack_bot_token)
        return self._bot_client 

    @property
    def user_client(self) -> WebClient:
        if self._user_client is None:
            self._user_client = WebClient(token=self.settings.slack_user_token)
        return self._user_client

    @property
    def socket_handler(self) -> SocketModeHandler:
        if self._socket_handler is None:
            self._socket_handler = SocketModeHandler(self.app, self.settings.slack_app_token)
        return self._socket_handler


slack_client = SlackClientManager()