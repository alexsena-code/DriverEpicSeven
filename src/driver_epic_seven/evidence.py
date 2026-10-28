from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from uuid import uuid4
from copy import deepcopy

import msgpack
from PIL import Image


def replace_evidence(temporary, target):
    # Windows readers may briefly hold the destination without delete sharing.
    # Retry only the atomic rename; never repeat capture or game input.
    for attempt in range(11):
        try:
            temporary.replace(target)
            return
        except PermissionError:
            if attempt == 10:
                raise
            time.sleep(.05)


class Evidence:
    def __init__(self, root: Path):
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
        self.path = root / name
        self.path.mkdir(parents=True)
        self.count = 0
        self.last_live = 0

    def write(self, name: str, data: dict):
        target=self.path / f"{name}.json"
        temporary=target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        replace_evidence(temporary, target)

    def frame(self, name: str, frame):
        path = self.path / f"{name}.png"
        temporary=path.with_name(f".{name}.pending.png")
        Image.fromarray(frame[:, :, :3][:, :, ::-1]).save(temporary)
        replace_evidence(temporary, path)
        return str(path)

    def recognized(self, name: str, frame, analysis: dict):
        self.count += 1
        # Limit disk growth even if a future graph loops incorrectly.
        if self.count <= 64:
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:100]
            stem = f"{self.count:03d}_{safe_name}"
            image_path = self.frame(stem, frame)
            self.write(stem, self.with_artifact(analysis, image_path, str(self.path / f"{stem}.json")))

    @staticmethod
    def with_artifact(analysis, frame_path, observation_path):
        if "ui_tree" not in analysis:
            return analysis
        data = deepcopy(analysis)
        data.update(frame=frame_path, observation_file=observation_path)
        data["observation_id"] = data["ui_tree"]["observation_id"]
        data["ui_tree"]["context"].update(frame=frame_path, observation_file=observation_path)
        return data

    def live(self, frame, analysis: dict):
        now=time.monotonic()
        if now-self.last_live>=3:
            self.last_live=now
            path=self.frame("live",frame)
            linked = self.with_artifact(analysis, path, str(self.path / "live.json"))
            self.write("live",{"epoch_seconds":time.time(),"frame":path,"analysis":linked})


def sentry_context(root: Path, fresh_seconds=10) -> dict:
    try:
        files = list(root.glob("*.run/__sentry-event"))
        if not files:
            return {"available": False}
        source = max(files, key=lambda item: item.stat().st_mtime)
        stat = source.stat()
        age = max(0, time.time()-stat.st_mtime)
        if stat.st_size > 2_000_000:
            return {"available": True, "fresh": False, "error": "event_too_large"}
        extra = msgpack.unpackb(source.read_bytes(), raw=False, strict_map_key=False).get("extra", {})
        allowed = {"scene": "scene.current", "last_command": "net.last_query_cmd",
                   "last_button": "ui.last_button", "back_stack": "ui.back_button_stack"}
        return {"available": True, "fresh": age <= fresh_seconds, "age_seconds": round(age, 2),
                **{name: str(extra[key])[:400] for name, key in allowed.items() if key in extra}}
    except (OSError, ValueError, TypeError, msgpack.UnpackException) as exc:
        return {"available": False, "error": type(exc).__name__}
