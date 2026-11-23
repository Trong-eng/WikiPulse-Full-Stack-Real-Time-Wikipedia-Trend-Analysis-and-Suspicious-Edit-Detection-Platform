"""Recording chỉ dùng local: giữ title gốc, thay user và loại comment nguồn."""

import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path


class RecordingError(Exception):
    """Không thể tạo hoặc ghi recording an toàn."""


REVERT = re.compile(r"^\s*(?:revert(?:ed|ing)?\b|undid\s+revision\b|undo\s+revision\b|"
                    r"rollback\b|rolled\s+back\b)", re.IGNORECASE)
ANONYMOUS_IP = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|^[0-9A-Fa-f]*:[0-9A-Fa-f:]+$")
TEMPORARY = re.compile(r"^~[0-9]{4}-[0-9]+-[0-9]+$")


def _is_link_or_junction(path):
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
    except FileNotFoundError:
        return False


class Recorder:
    def __init__(self, path, root, *, secret=None):
        root = Path(root).absolute()
        path = Path(path).absolute()
        try:
            path.resolve().relative_to(root.resolve())
            relative = path.relative_to(root)
            candidates = [root.parent, root]
            for part in relative.parts[:-1]:
                candidates.append(candidates[-1] / part)
            if any(_is_link_or_junction(p) for p in candidates):
                raise ValueError("recording path uses symlink or junction")
            root.mkdir(parents=True, exist_ok=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            self.file = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
        except (OSError, ValueError) as exc:
            raise RecordingError("cannot create recording") from exc
        self.secret = secret if secret is not None else secrets.token_bytes(32)

    def prepare(self, line):
        try:
            source = json.loads(line)
        except (ValueError, TypeError):
            return None
        if not isinstance(source, dict):
            return None
        result = {}
        for key in ("wiki", "title", "type"):
            if isinstance(source.get(key), str):
                result[key] = source[key]
        for key in ("id", "timestamp", "page_id", "namespace"):
            if isinstance(source.get(key), int) and not isinstance(source[key], bool):
                result[key] = source[key]
        for key in ("bot", "minor"):
            if isinstance(source.get(key), bool):
                result[key] = source[key]
        for key in ("length", "revision"):
            value = source.get(key)
            if isinstance(value, dict):
                result[key] = {k: value[k] for k in ("old", "new")
                               if isinstance(value.get(k), int) and not isinstance(value[k], bool)}
        meta = source.get("meta")
        if isinstance(meta, dict):
            result["meta"] = {k: meta[k] for k in ("id", "dt", "domain")
                              if isinstance(meta.get(k), str)}
        user = source.get("user")
        if isinstance(user, str) and user.strip():
            digest = hmac.new(self.secret, user.encode("utf-8", "surrogatepass"),
                              hashlib.sha256).hexdigest()
            result["user"] = "Editor_" + digest
        source_anon = source.get("anon")
        ip = bool(isinstance(user, str) and ANONYMOUS_IP.fullmatch(user))
        temporary = bool(isinstance(user, str) and TEMPORARY.fullmatch(user))
        result["anon"] = (source_anon if isinstance(source_anon, bool) else ip) or temporary
        comment = source.get("comment")
        event_type = source.get("type")
        if isinstance(event_type, str) and event_type.strip().lower() == "edit" and isinstance(comment, str):
            if REVERT.match(comment):
                result["comment"] = "Reverted"
        return result

    def write(self, record):
        if record is not None:
            try:
                self.file.write(json.dumps(record, ensure_ascii=True) + "\n")
                self.file.flush()
            except (OSError, ValueError) as exc:
                raise RecordingError("cannot write recording") from exc

    def close(self):
        try:
            self.file.close()
        except OSError as exc:
            raise RecordingError("cannot close recording") from exc
