"""
Jury Command Handler
/jury [join|leave|list] komutu burada işlenir.
"""
from __future__ import annotations

from slack_bolt import App

from packages.slack.client import slack_client
from ...core.event_loop import run_async
from ...core.queue.challenge_queue import QueueItem
from ...logger import _logger
from ...manager import service_manager

app: App = slack_client.app


@app.command("/jury")
def handle_jury_command(ack, body: dict, client) -> None:
    ack()
    args = body.get("text", "").strip().split()
    handle_jury(client, body, args)


def handle_jury(client, body: dict, args: list[str]) -> None:
    """
    `/jury [join|leave|list]` alt komutlarını yönlendirir.
    """
    user_id = body["user_id"]
    channel_id = body["channel_id"]
    sub = args[0].lower() if len(args) > 0 else "join"

    if sub == "join":
        _handle_jury_join(client, user_id, channel_id)
    elif sub == "leave":
        _handle_jury_leave(client, user_id, channel_id)
    elif sub == "list":
        _handle_jury_list(client, user_id, channel_id)
    else:
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="❓ Kullanım: `/jury [join|leave|list]`"
        )


def _handle_jury_join(client, user_id: str, channel_id: str) -> None:
    added = service_manager.jury_queue.add(QueueItem(slack_id=user_id))
    if not added:
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="🧐 Zaten jüri kuyruğundasınız."
        )
        return

    _logger.info("[CMD] %s joined jury queue", user_id)
    client.chat_postEphemeral(
        channel=channel_id, user=user_id,
        text=(
            "✅ Jüri kuyruğuna eklendiniz!\n"
            "Bekleyen bir challenge varsa hemen atanırsınız; yoksa yeni bir challenge teslim edildiğinde çağrılırsınız."
        )
    )

    # Bekleyen (COMPLETED, jüri atanmamış) challenge var mı?
    from ..events.internal import _try_assign_waiting_challenges
    run_async(_try_assign_waiting_challenges())

    # Kullanıcı hemen atandıysa (kuyruktan çıkarıldıysa) bildir
    if not service_manager.jury_queue.is_in_queue(user_id):
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="⚡ Bekleyen bir challenge bulundu — değerlendirme ekibine atandınız! Değerlendirme kanalına davet bekleniyor."
        )


def _handle_jury_leave(client, user_id: str, channel_id: str) -> None:
    removed = service_manager.jury_queue.remove(user_id)
    if removed:
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="👋 Jüri kuyruğundan çıkarıldınız."
        )
    else:
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="🧐 Jüri kuyruğunda değilsiniz."
        )


def _handle_jury_list(client, user_id: str, channel_id: str) -> None:
    count = service_manager.jury_queue.count()
    if count == 0:
        text = "📭 Jüri kuyruğu şu an boş."
    else:
        order = service_manager.jury_queue.get_order()
        lines = [f"{i + 1}. <@{uid}>" for i, uid in enumerate(order)]
        text = f"👥 Jüri kuyruğu (*{count} kişi*):\n" + "\n".join(lines)
    client.chat_postEphemeral(channel=channel_id, user=user_id, text=text)
