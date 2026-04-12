"""Modal submit ve buton action handler'ları."""

import logging
from packages.slack.client import slack_client
from packages.slack.blocks.layouts import Layouts
from services.feature_request_service.core.event_loop import run_async
from services.feature_request_service.service import FeatureRequestService

logger = logging.getLogger("feature_request_service.handlers.events")
app = slack_client.app
_service = None


def _svc():
    global _service
    if _service is None:
        _service = FeatureRequestService()
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
        client.chat_postMessage(channel=uid, text="❌ Teknik hata.")
        return
    match r.get("status"):
        case "created":
            client.chat_postMessage(
                channel=uid,
                blocks=Layouts.feature_request_success(raw),
                text="Kaydedildi!",
            )
        case "similar_found":
            client.chat_postMessage(
                channel=uid,
                blocks=Layouts.feature_request_similar(
                    r["existing_text"], r["existing_id"]
                ),
                text="Benzer var.",
            )
        case "quota_exceeded":
            client.chat_postMessage(
                channel=uid,
                blocks=Layouts.feature_request_quota_exceeded(r["used"], r["max"]),
                text="Hak doldu.",
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
        client.chat_postMessage(
            channel=uid,
            blocks=Layouts.feature_request_success(txt),
            text="Güncellendi!",
        )
    except Exception as e:
        logger.error(f"Edit hatası: {e}", exc_info=True)
        client.chat_postMessage(channel=uid, text="❌ Güncelleme hatası.")


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
    client.chat_postMessage(
        channel=body["user"]["id"],
        text="Tamam! `/cemilimyapar` ile yeni fikir gönderebilirsin. 💡",
    )
