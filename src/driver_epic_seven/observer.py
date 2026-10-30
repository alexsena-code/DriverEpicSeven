"""Shared read-only view of existing observations; never captures or acts."""

from collections import deque
from copy import deepcopy
import json
from pathlib import Path
from threading import RLock
import time

from .observed_ui import screen_state, validate_tree


class SharedObserver:
    def __init__(self, writer=None):
        self._lock = RLock()
        self._latest = None
        self._events = deque(maxlen=64)
        self._sequence = 0
        self._revision = 0
        self._invalidated = None
        self._closed = False
        self._writer = writer
        self.metrics = {"driver_captures": 0, "recognitions": 0, "publications": 0,
                        "cache_hits": 0, "refreshes": 0, "analysis_wall_ms": 0,
                        "analysis_cpu_ms": 0, "publication_wall_ms": 0,
                        "candidate_rejections": 0, "candidate_rejection_wall_ms": 0}

    def count(self, key, amount=1):
        with self._lock:
            self.metrics[key] += amount

    @staticmethod
    def _values(tree):
        # Compare meanings, not timestamps, confidence jitter or animation pixels.
        return {key: {name: value["value"] for name, value in item["fields"].items()
                      if name not in ("box", "anchor_box", "match_score")}
                for key, item in tree["nodes"].items()}

    def _event(self, kind, **fields):
        self._sequence += 1
        self._events.append({"sequence": self._sequence, "kind": kind,
                             "available_at_epoch_seconds": time.time(), **fields})

    def publish(self, observation, source):
        started = time.perf_counter()
        tree = observation["ui_tree"]
        validate_tree(tree)
        with self._lock:
            if self._closed:
                return
            previous = self._values(self._latest["ui_tree"]) if self._latest else {}
            current = self._values(tree)
            added = sorted(current.keys() - previous.keys())
            removed = sorted(previous.keys() - current.keys())
            changed = sorted(k for k in current.keys() & previous.keys() if current[k] != previous[k])
            if added or removed or changed:
                self._event("tree_changed", before_state=screen_state(self._latest) if self._latest else None,
                            after_state=screen_state(observation), added_nodes=added,
                            removed_nodes=removed, changed_nodes=changed)
            self._revision += 1
            self._invalidated = None
            self._latest = {"ui_tree": deepcopy(tree), "source": source,
                            "captured_at_epoch_seconds": observation.get("captured_at_epoch_seconds"),
                            "available_at_epoch_seconds": time.time(),
                            "window": deepcopy(observation["window"])}
            self.metrics["publications"] += 1
            self.metrics["publication_wall_ms"] += (time.perf_counter() - started) * 1000
            self._write()

    def invalidate(self, reason, **fields):
        with self._lock:
            if self._closed:
                return
            self._invalidated = reason
            self._closed = reason == "disconnected"
            self._event("invalidated", reason=reason, **fields)
            self._write()

    def event(self, kind, **fields):
        with self._lock:
            self._event(kind, **fields)
            self._write()

    def _write(self):
        if self._writer:
            self._writer("observer", self.snapshot())

    def snapshot(self, max_age_ms=500, after_sequence=0, window=None, now=None):
        if not 0 <= max_age_ms <= 30000:
            raise ValueError("Validade do snapshot deve estar entre 0 e 30000 ms.")
        now = time.time() if now is None else now
        with self._lock:
            latest = deepcopy(self._latest)
            reasons = []
            captured = latest.get("captured_at_epoch_seconds") if latest else None
            age = (now - captured) * 1000 if captured is not None else None
            if not latest:
                reasons.append("no_snapshot")
            elif captured is None:
                reasons.append("capture_time_unknown")
            elif age < 0 or age > max_age_ms:
                reasons.append("expired_or_clock_changed")
            if self._invalidated:
                reasons.append(self._invalidated)
            if latest and window is not None:
                if window.get("minimized") or any(window.get(k) != latest["window"].get(k)
                        for k in ("hwnd", "pid", "process_name", "window_title", "window_class", "client_size")):
                    reasons.append("window_changed")
            return {"snapshot_revision": self._revision, "event_sequence": self._sequence,
                    "readonly": True, "snapshot": latest, "invalidated_reason": self._invalidated,
                    "validity": {"valid": not reasons, "age_ms": age,
                                 "max_age_ms": max_age_ms, "reasons": reasons},
                    "events": deepcopy([event for event in self._events if event["sequence"] > after_sequence]),
                    "history_lost": bool(self._events and after_sequence < self._events[0]["sequence"] - 1),
                    "metrics": dict(self.metrics)}


def read_snapshot_file(path, max_age_ms=500, after_sequence=0, window=None, now=None):
    """Re-evaluate exported freshness now; a saved 'valid' flag can expire."""
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("Snapshot excede o limite de leitura.")
    data = json.loads(path.read_text(encoding="utf-8"))
    observer = SharedObserver()
    latest = data["snapshot"]
    if latest is not None:
        validate_tree(latest["ui_tree"])
    observer._latest = latest
    observer._revision = data["snapshot_revision"]
    observer._sequence = data["event_sequence"]
    observer._invalidated = data.get("invalidated_reason")
    observer._events.extend(data["events"])
    observer.metrics = data["metrics"]
    return observer.snapshot(max_age_ms, after_sequence, window, now)
