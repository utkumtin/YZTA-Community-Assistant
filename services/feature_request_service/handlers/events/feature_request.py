"""Modal submit ve buton action handler'ları."""

import logging

from packages.database.manager import db
from packages.slack.blocks.layouts import Layouts
from packages.slack.client import slack_client
from services.feature_request_service.core.event_loop import run_async
from services.feature_request_service.service import FeatureRequestService
from services.feature_request_service.utils.notifications import (
    NotificationType,
    send_notification,
)

logger = logging.getLogger("feature_request_service.handlers.events")
app = slack_client.app
_service = None


def _svc():
    global _service
    if _service is None:
        _service = FeatureRequestService(db)
    return _service


@app.view("feature_request_modal")
def handle_submit(ack, body, client):
    ack()
    uid = body["user"]["id"]
    raw = body["view"]["state"]["values"]["feature_input_block"]["feature_text_input"][
        "value"
    ]
    try:
        r = run_async(_svc().submit_request(uid, raw))
    except Exception as e:
        logger.error(f"Submit hatası: {e}", exc_info=True)
        send_notification(
            client, uid, uid, NotificationType.ACTION_RESULT, "❌ Teknik hata."
        )
        return
    match r.get("status"):
        case "created":
            send_notification(
                client,
                uid,
                uid,
                NotificationType.ACTION_RESULT,
                "Kaydedildi!",
                Layouts.feature_request_success(raw),
            )
        case "similar_found":
            send_notification(
                client,
                uid,
                uid,
                NotificationType.ACTION_RESULT,
                "Benzer var.",
                Layouts.feature_request_similar(r["existing_text"], r["existing_id"]),
            )
        case "quota_exceeded":
            send_notification(
                client,
                uid,
                uid,
                NotificationType.ACTION_RESULT,
                "Hak doldu.",
                Layouts.feature_request_quota_exceeded(r["used"], r["max"]),
            )


@app.view("feature_request_edit_modal")
def handle_edit_submit(ack, body, client):
    ack()
    uid = body["user"]["id"]
    rid = body["view"]["private_metadata"]
    txt = body["view"]["state"]["values"]["feature_input_block"]["feature_text_input"][
        "value"
    ]
    try:
        run_async(_svc().update_request(rid, txt))
        send_notification(
            client,
            uid,
            uid,
            NotificationType.ACTION_RESULT,
            "Güncellendi!",
            Layouts.feature_request_success(txt),
        )
    except Exception as e:
        logger.error(f"Edit hatası: {e}", exc_info=True)
        send_notification(
            client, uid, uid, NotificationType.ACTION_RESULT, "❌ Güncelleme hatası."
        )


@app.action("feature_edit_yes")
def handle_edit_yes(ack, body, client):
    ack()
    rid = body["actions"][0]["value"]
    try:
        txt = run_async(_svc().get_request_text(rid))
        client.views_open(
            trigger_id=body["trigger_id"],
            view=Layouts.feature_request_edit_modal(txt, rid),
        )
    except Exception as e:
        logger.error(f"Edit modal hatası: {e}", exc_info=True)


@app.action("feature_edit_no")
def handle_edit_no(ack, body, client):
    ack()
    uid = body["user"]["id"]
    send_notification(
        client,
        uid,
        uid,
        NotificationType.ACTION_RESULT,
        "Tamam! `/cemilimyapar` ile yeni fikir gönderebilirsin. 💡",
    )
