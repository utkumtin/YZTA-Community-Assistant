"""
/cemilimyapar ve /cemil-report slash komut handler'ları.
"""

import logging

from packages.database.manager import db
from packages.settings import get_settings
from packages.slack.blocks.layouts import Layouts
from packages.slack.client import slack_client
from services.feature_request_service.core.event_loop import run_async
from services.feature_request_service.service import FeatureRequestService
from services.feature_request_service.utils.notifications import (
    NotificationType,
    send_notification,
)

logger = logging.getLogger("feature_request_service.handlers.commands")
app = slack_client.app
_service = None


def _svc():
    global _service
    if _service is None:
        _service = FeatureRequestService(db)
    return _service


@app.command("/cemilimyapar")
def handle_cemilimyapar(ack, body, client):
    ack()
    channel_id = body.get("channel_id", "")
    client.views_open(
        trigger_id=body["trigger_id"],
        view=Layouts.feature_request_modal(channel_id=channel_id),
    )


@app.command("/cemil-report")
def handle_cemil_report(ack, body, client):
    ack()
    uid = body["user_id"]
    txt = body.get("text", "").strip()
    s = get_settings()
    admins = s.slack_admins
    if uid not in admins:
        send_notification(
            client,
            uid,
            uid,
            NotificationType.COMMAND_ERROR,
            "❌ Bu komut sadece adminler içindir.",
        )
        return
    if txt != "feature-requests":
        send_notification(
            client,
            uid,
            uid,
            NotificationType.COMMAND_ERROR,
            f"Bilinmeyen: `{txt}`\nKullanım: `/cemil-report feature-requests`",
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
        send_notification(
            client,
            uid,
            uid,
            NotificationType.SYSTEM_REPORT,
            "Rapor",
            blocks,
        )
    except Exception as e:
        logger.error(f"Rapor hatası: {e}", exc_info=True)
        send_notification(
            client, uid, uid, NotificationType.COMMAND_ERROR, "❌ Rapor hatası."
        )
