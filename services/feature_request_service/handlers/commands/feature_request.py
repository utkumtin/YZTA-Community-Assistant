"""
/cemilimyapar ve /cemil-report slash komut handler'ları.
"""

import logging
from packages.slack.client import slack_client
from packages.slack.blocks.layouts import Layouts
from packages.settings import get_settings
from services.feature_request_service.core.event_loop import run_async
from services.feature_request_service.service import FeatureRequestService

logger = logging.getLogger("feature_request_service.handlers.commands")
app = slack_client.app
_service = None


def _svc():
    global _service
    if _service is None:
        _service = FeatureRequestService()
    return _service


@app.command("/cemilimyapar")
def handle_cemilimyapar(ack, body, client):
    ack()
    client.views_open(
        trigger_id=body["trigger_id"], view=Layouts.feature_request_modal()
    )


@app.command("/cemil-report")
def handle_cemil_report(ack, body, client):
    ack()
    uid = body["user_id"]
    txt = body.get("text", "").strip()
    s = get_settings()
    admins = (
        s.slack_admins
        if isinstance(s.slack_admins, list)
        else [a.strip() for a in s.slack_admins.split(",")]
    )
    if uid not in admins:
        client.chat_postMessage(
            channel=uid, text="❌ Bu komut sadece adminler içindir."
        )
        return
    if txt != "feature-requests":
        client.chat_postMessage(
            channel=uid,
            text=f"Bilinmeyen: `{txt}`\nKullanım: `/cemil-report feature-requests`",
        )
        return
    try:
        cr = run_async(_svc().run_clustering_pipeline())
        rt = run_async(_svc().generate_admin_report())
        blocks = Layouts.feature_request_report(rt)
        if cr and "clustering_log" in cr:
            blocks.extend(
                Layouts.feature_request_calibration_summary(cr["clustering_log"])
            )
        client.chat_postMessage(channel=uid, blocks=blocks, text="Rapor")
    except Exception as e:
        logger.error(f"Rapor hatası: {e}", exc_info=True)
        client.chat_postMessage(channel=uid, text="❌ Rapor hatası.")
