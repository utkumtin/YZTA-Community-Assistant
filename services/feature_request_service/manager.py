"""Feature Request Service Manager — Singleton orkestratör."""

import logging
from typing import Optional
from packages.database.manager import db

_logger = logging.getLogger("feature_request_service.manager")


class FeatureRequestServiceManager:
    _instance: Optional["FeatureRequestServiceManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._monitor = None  # Adım 10'da set edilecek
        self._initialized = True
        _logger.info("[SVC] Feature request manager init")

    async def start(self):
        _logger.info("[SVC] Starting...")
        if self._monitor:
            await self._monitor.start()
        _logger.info("[SVC] Started")

    async def stop(self):
        _logger.info("[SVC] Stopping...")
        if self._monitor:
            await self._monitor.stop()
        _logger.info("[SVC] Stopped")


service_manager = FeatureRequestServiceManager()
