from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

from ...logger import _logger
from ...utils.datetime_helpers import _utc_now


ATTEMPT_PENALTY: float = 0.5


@dataclass
class QueueItem:
    slack_id: str
    joined_at: datetime = field(default_factory=_utc_now)
    attempts: int = field(default=0)
    multiplier: float = field(default=1.0)

    def score(self) -> float:
        wait_sec = (_utc_now() - self.joined_at).total_seconds()
        return wait_sec / (1.0 + self.attempts * ATTEMPT_PENALTY * self.multiplier)

    def __str__(self) -> str:
        return f"{self.slack_id} - {self.joined_at} - {self.score()}"

    def __repr__(self) -> str:
        return f"<QueueItem {self.slack_id} - {self.joined_at} - {self.score()}>"


class CustomQueue:
    def __init__(self, name: str, attempt_penalty: float = ATTEMPT_PENALTY):
        self.name = name
        self._lock = RLock()
        self.attempt_penalty = attempt_penalty
        self._items: dict[str, QueueItem] = {}
        self._order: list[str] = []

    def _reorder(self) -> None:
        """Lock alındıktan sonra çağrılmalı."""
        self._order = sorted(
            self._items,
            key=lambda uid: self._items[uid].score(),
            reverse=True,
        )

    def add(self, item: QueueItem) -> bool:
        with self._lock:
            if item.slack_id in self._items:
                _logger.warning(f"User {item.slack_id} already in queue {self.name}")
                return False
            self._items[item.slack_id] = item
            self._reorder()
            pos = self._order.index(item.slack_id) + 1
            _logger.info(
                "[Q:%s] add %s pos=%s", self.name, item.slack_id, pos,
                extra={"queue": {"name": self.name, "size": len(self._items), "action": "add", "value": item.slack_id}},
            )
            return True

    def remove(self, slack_id: str) -> bool:
        with self._lock:
            if slack_id not in self._items:
                _logger.warning("[Q:%s] remove: %s not in queue", self.name, slack_id)
                return False
            del self._items[slack_id]
            self._reorder()
            _logger.info(
                "[Q:%s] remove %s", self.name, slack_id,
                extra={"queue": {"name": self.name, "size": len(self._items), "action": "remove", "value": slack_id}},
            )
            return True

    def update(self, slack_id: str, **kwargs) -> bool:
        with self._lock:
            if slack_id not in self._items:
                _logger.warning("[Q:%s] update: %s not in queue", self.name, slack_id)
                return False
            item = self._items[slack_id]
            for key, value in kwargs.items():
                setattr(item, key, value)
            self._reorder()
            pos = self._order.index(slack_id) + 1
            _logger.info(
                "[Q:%s] update %s pos=%s", self.name, slack_id, pos,
                extra={"queue": {"name": self.name, "size": len(self._items), "action": "update", "value": slack_id}},
            )
            return True

    def peek(self) -> QueueItem | None:
        with self._lock:
            if not self._order:
                return None
            return self._items[self._order[0]]

    def pop(self) -> QueueItem | None:
        with self._lock:
            if not self._order:
                return None
            slack_id = self._order.pop(0)
            item = self._items.pop(slack_id)
            _logger.info(
                "[Q:%s] pop %s", self.name, slack_id,
                extra={"queue": {"name": self.name, "size": len(self._items), "action": "pop", "value": slack_id}},
            )
            return item

    def pop_n(self, n: int) -> list[QueueItem]:
        with self._lock:
            if n > len(self._order):
                return []
            taken = self._order[:n]
            items = [self._items.pop(slack_id) for slack_id in taken]
            self._order = self._order[n:]
            _logger.info(
                "[Q:%s] pop_n %s", self.name, n,
                extra={"queue": {"name": self.name, "size": len(self._items), "action": "pop_n", "value": n}},
            )
            return items

    def get_position(self, slack_id: str) -> int:
        with self._lock:
            if slack_id not in self._items:
                _logger.warning(f"User {slack_id} not in queue {self.name}")
                return -1
            return self._order.index(slack_id) + 1

    def is_in_queue(self, slack_id: str) -> bool:
        with self._lock:
            return slack_id in self._items

    def get_order(self) -> list[str]:
        with self._lock:
            return self._order.copy()

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def count_excluding(self, exclude_ids: set[str]) -> int:
        """exclude_ids dışındaki üye sayısını döner."""
        with self._lock:
            return sum(1 for uid in self._items if uid not in exclude_ids)

    def pop_n_excluding(self, n: int, exclude_ids: set[str]) -> list[QueueItem]:
        """En yüksek skorlu n kişiyi exclude_ids dışından çeker; yeterli kişi yoksa boş liste döner."""
        with self._lock:
            eligible = [uid for uid in self._order if uid not in exclude_ids]
            if len(eligible) < n:
                return []
            taken = eligible[:n]
            items = [self._items.pop(slack_id) for slack_id in taken]
            taken_set = set(taken)
            self._order = [uid for uid in self._order if uid not in taken_set]
            _logger.info(
                "[Q:%s] pop_n_excluding %s (excluded=%s)", self.name, n, len(exclude_ids),
                extra={"queue": {"name": self.name, "size": len(self._items), "action": "pop_n_excluding", "value": n}},
            )
            return items

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._order.clear()
            _logger.info("[Q:%s] cleared", self.name)