"""Внешний истинный рандом: атмосферный шум random.org, квантовый ANU, fallback secrets."""

from __future__ import annotations

import json
import logging
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid

from backend.config import RANDOM_ORG_API_KEY, TRUE_RANDOM_ENABLED, TRUE_RANDOM_TIMEOUT

log = logging.getLogger(__name__)

_lock = threading.Lock()
_last_source = "secrets"


def last_random_source() -> str:
    with _lock:
        return _last_source


def _set_source(name: str) -> None:
    global _last_source
    with _lock:
        _last_source = name


def _http_get(url: str, *, timeout: float | None = None) -> str:
    timeout = TRUE_RANDOM_TIMEOUT if timeout is None else timeout
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DOTAG3-Game/1.0 (true-random)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace").strip()


def _fetch_random_org_plain(n: int, min_v: int, max_v: int) -> list[int] | None:
    params = urllib.parse.urlencode(
        {
            "num": n,
            "min": min_v,
            "max": max_v,
            "col": 1,
            "base": 10,
            "format": "plain",
            "rnd": "new",
        }
    )
    url = f"https://www.random.org/integers/?{params}"
    try:
        body = _http_get(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        log.debug("random.org plain failed: %s", exc)
        return None

    values: list[int] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            values.append(int(line))
        except ValueError:
            log.debug("random.org plain bad line: %r", line)
            return None
    if len(values) != n:
        log.debug("random.org plain count mismatch: %s", len(values))
        return None
    for v in values:
        if v < min_v or v > max_v:
            return None
    return values


def _fetch_random_org_json(n: int, min_v: int, max_v: int) -> list[int] | None:
    if not RANDOM_ORG_API_KEY:
        return None
    payload = {
        "jsonrpc": "2.0",
        "method": "generateIntegers",
        "params": {
            "apiKey": RANDOM_ORG_API_KEY,
            "n": n,
            "min": min_v,
            "max": max_v,
            "replacement": True,
        },
        "id": str(uuid.uuid4()),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.random.org/json-rpc/4/invoke",
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DOTAG3-Game/1.0 (true-random)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TRUE_RANDOM_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        log.debug("random.org json failed: %s", exc)
        return None

    if body.get("error"):
        log.debug("random.org json error: %s", body["error"])
        return None
    result = body.get("result", {})
    values = result.get("random", {}).get("data")
    if not isinstance(values, list) or len(values) != n:
        return None
    try:
        ints = [int(v) for v in values]
    except (TypeError, ValueError):
        return None
    for v in ints:
        if v < min_v or v > max_v:
            return None
    return ints


def _fetch_anu_uint16(n: int) -> list[int] | None:
    params = urllib.parse.urlencode({"length": n, "type": "uint16"})
    url = f"https://api.qrng.anu.edu.au/?{params}"
    try:
        body = _http_get(url)
        data = json.loads(body)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        log.debug("ANU QRNG failed: %s", exc)
        return None
    if not data.get("success"):
        return None
    raw = data.get("data")
    if not isinstance(raw, list) or len(raw) != n:
        return None
    try:
        return [int(v) & 0xFFFF for v in raw]
    except (TypeError, ValueError):
        return None


def _integers_from_anu(n: int, min_v: int, max_v: int) -> list[int] | None:
    span = max_v - min_v + 1
    if span <= 0:
        return None
    raw = _fetch_anu_uint16(max(n, 4))
    if not raw:
        return None
    out: list[int] = []
    idx = 0
    while len(out) < n:
        if idx >= len(raw):
            extra = _fetch_anu_uint16(8)
            if not extra:
                return None
            raw.extend(extra)
        value = raw[idx]
        idx += 1
        limit = (0x10000 // span) * span
        if value >= limit:
            continue
        out.append(min_v + (value % span))
    return out


def fetch_integers(n: int, min_v: int, max_v: int) -> list[int] | None:
    """Запросить n целых в [min_v, max_v] из внешнего источника."""
    if n <= 0 or min_v > max_v:
        return None
    if not TRUE_RANDOM_ENABLED:
        return None

    values = _fetch_random_org_json(n, min_v, max_v)
    if values:
        _set_source("random.org (API)")
        return values

    values = _fetch_random_org_plain(n, min_v, max_v)
    if values:
        _set_source("random.org (атмосферный шум)")
        return values

    values = _integers_from_anu(n, min_v, max_v)
    if values:
        _set_source("ANU Quantum RNG")
        return values

    return None


def randint(a: int, b: int) -> int:
    if a > b:
        raise ValueError("empty range")
    values = fetch_integers(1, a, b)
    if values:
        return values[0]
    _set_source("secrets (OS CSPRNG)")
    return secrets.randbelow(b - a + 1) + a


def randbelow(n: int) -> int:
    if n <= 0:
        raise ValueError("n must be positive")
    return randint(0, n - 1)


def choice(seq):
    return seq[randbelow(len(seq))]


def sample(seq, k: int):
    items = list(seq)
    if k >= len(items):
        return secrets.SystemRandom().sample(items, len(items))
    return secrets.SystemRandom().sample(items, k)


def shuffle(seq):
    items = list(seq)
    secrets.SystemRandom().shuffle(items)
    return items


def random_meta() -> dict[str, str]:
    return {"randomSource": last_random_source()}
