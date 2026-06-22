"""Private Calendar + 3M Whiteboard API for the VIPZone service.

These endpoints back the personal, private tool at ``/tools/calendar/`` on
seomoney.org (calendar events + sticky-note whiteboard). They are NOT public:
every read/write requires the SAME GitHub-OAuth session the blog editor uses,
restricted to the admin allowlist (``ADMIN_EMAILS`` / ``ADMIN_USERNAMES`` /
repo-superadmin). Data lives server-side in the VIPZone SQLite store keyed by the
authenticated owner email — never in cookies, public static JSON, or the repo —
so clearing cookies only ends the session: re-login restores everything.

Auth is reused, not reinvented: :func:`cms_auth.session_dep` resolves the Bearer
``sid`` to a profile, and :func:`require_owner` enforces the admin allowlist with
the same predicates the CMS admin routes use.

Routes (all require ``Authorization: Bearer <sid>`` of an allowlisted admin):
  GET    /calendar/events
  POST   /calendar/events
  PATCH  /calendar/events/{event_id}
  PUT    /calendar/events/{event_id}
  DELETE /calendar/events/{event_id}
  GET    /whiteboard/notes
  POST   /whiteboard/notes
  PATCH  /whiteboard/notes/{note_id}
  PUT    /whiteboard/notes/{note_id}
  DELETE /whiteboard/notes/{note_id}
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from cms_auth import is_admin, session_dep
from roles import is_superadmin

router = APIRouter(tags=["personal"])

# DB getter injected by configure() from the host app (main.py) — avoids importing
# main at module load (mirrors the cms_repo / gsc wiring pattern).
_get_db: Optional[Callable[[], Any]] = None


def configure(get_db: Callable[[], Any]) -> None:
    global _get_db
    _get_db = get_db


def _db() -> Any:
    if _get_db is None:  # pragma: no cover - configure() always called at mount
        raise HTTPException(503, "personal_data_not_configured")
    return _get_db()


async def require_owner(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    """Authenticated AND on the admin allowlist — this is a personal/private tool.

    session_dep already rejects missing/expired sessions (401). We add the same
    admin gate the CMS admin routes use so only the blog owner reaches the data.
    """
    if not is_admin(profile.get("email"), profile.get("username")) and not is_superadmin(profile):
        raise HTTPException(403, "admin_only")
    email = (profile.get("email") or "").lower().strip()
    if not email:
        # Allowlisted by username but no verified email → no stable owner key.
        raise HTTPException(403, "no_owner_email")
    return profile


def _owner(profile: dict[str, Any]) -> str:
    return (profile.get("email") or "").lower().strip()


# ============= sanitisation =============
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MAX_TEXT = 5000
MAX_TITLE = 500
MAX_SHORT = 500
MAX_DATETIME = 40

CALENDAR_COLORS = {"teal", "blue", "purple", "amber", "green", "red", "pink"}
NOTE_COLORS = {"yellow", "green", "blue", "pink", "purple", "orange", "white"}
EVENT_STATUSES = {"", "confirmed", "tentative", "cancelled", "done", "busy", "free"}


def _clean(value: Any, limit: int) -> str:
    """Strip control chars + cap length. Non-strings collapse to ''."""
    if not isinstance(value, str):
        return ""
    return _CONTROL_RE.sub("", value).strip()[:limit]


def _clean_datetime(value: Any) -> str:
    """Accept the calendar's local-ISO strings (YYYY-MM-DD[ THH:MM]); cap length."""
    s = _clean(value, MAX_DATETIME)
    return s


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid_json")
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_body")
    return body


def _sanitize_event(body: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    """Validate/normalise an event payload. ``partial`` keeps absent keys as None
    (PATCH semantics) so the DB merge layer preserves existing values."""
    out: dict[str, Any] = {}

    def present(key: str) -> bool:
        return key in body

    if present("title") or not partial:
        out["title"] = _clean(body.get("title"), MAX_TITLE) or "(Không tiêu đề)"
    if present("start") or not partial:
        start = _clean_datetime(body.get("start"))
        if not start:
            raise HTTPException(400, "missing_start")
        out["start"] = start
    if present("end") or not partial:
        out["end"] = _clean_datetime(body.get("end")) or out.get("start", "")
    if present("allDay") or not partial:
        out["allDay"] = bool(body.get("allDay"))
    if present("color") or not partial:
        color = _clean(body.get("color"), 20) or "teal"
        out["color"] = color if color in CALENDAR_COLORS else "teal"
    if present("location"):
        out["location"] = _clean(body.get("location"), MAX_SHORT)
    elif not partial:
        out["location"] = ""
    if present("notes"):
        out["notes"] = _clean(body.get("notes"), MAX_TEXT)
    elif not partial:
        out["notes"] = ""
    if present("status"):
        status = _clean(body.get("status"), 20).lower()
        out["status"] = status if status in EVENT_STATUSES else ""
    elif not partial:
        out["status"] = ""
    return out


def _sanitize_note(body: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "text" in body or not partial:
        out["text"] = _clean(body.get("text"), MAX_TEXT)
    if "color" in body or not partial:
        color = _clean(body.get("color"), 20) or "yellow"
        out["color"] = color if color in NOTE_COLORS else "yellow"
    if "order" in body:
        try:
            out["order"] = int(body.get("order"))
        except (TypeError, ValueError):
            raise HTTPException(400, "invalid_order")
    return out


# ============= Calendar events =============
@router.get("/calendar/events")
async def list_events(profile: dict[str, Any] = Depends(require_owner)) -> dict[str, Any]:
    return {"events": _db().list_calendar_events(_owner(profile))}


@router.post("/calendar/events", status_code=201)
async def create_event(
    request: Request, profile: dict[str, Any] = Depends(require_owner)
) -> dict[str, Any]:
    body = await _json_body(request)
    data = _sanitize_event(body, partial=False)
    event = _db().create_calendar_event(_owner(profile), data)
    return {"event": event}


@router.api_route("/calendar/events/{event_id}", methods=["PATCH", "PUT"])
async def update_event(
    event_id: str, request: Request, profile: dict[str, Any] = Depends(require_owner)
) -> dict[str, Any]:
    body = await _json_body(request)
    data = _sanitize_event(body, partial=True)
    event = _db().update_calendar_event(_owner(profile), event_id, data)
    if not event:
        raise HTTPException(404, "event_not_found")
    return {"event": event}


@router.delete("/calendar/events/{event_id}")
async def delete_event(
    event_id: str, profile: dict[str, Any] = Depends(require_owner)
) -> dict[str, Any]:
    if not _db().delete_calendar_event(_owner(profile), event_id):
        raise HTTPException(404, "event_not_found")
    return {"ok": True, "deleted": event_id}


# ============= Whiteboard sticky notes =============
@router.get("/whiteboard/notes")
async def list_notes(profile: dict[str, Any] = Depends(require_owner)) -> dict[str, Any]:
    return {"notes": _db().list_whiteboard_notes(_owner(profile))}


@router.post("/whiteboard/notes", status_code=201)
async def create_note(
    request: Request, profile: dict[str, Any] = Depends(require_owner)
) -> dict[str, Any]:
    body = await _json_body(request)
    data = _sanitize_note(body, partial=False)
    note = _db().create_whiteboard_note(_owner(profile), data)
    return {"note": note}


@router.api_route("/whiteboard/notes/{note_id}", methods=["PATCH", "PUT"])
async def update_note(
    note_id: str, request: Request, profile: dict[str, Any] = Depends(require_owner)
) -> dict[str, Any]:
    body = await _json_body(request)
    data = _sanitize_note(body, partial=True)
    note = _db().update_whiteboard_note(_owner(profile), note_id, data)
    if not note:
        raise HTTPException(404, "note_not_found")
    return {"note": note}


@router.delete("/whiteboard/notes/{note_id}")
async def delete_note(
    note_id: str, profile: dict[str, Any] = Depends(require_owner)
) -> dict[str, Any]:
    if not _db().delete_whiteboard_note(_owner(profile), note_id):
        raise HTTPException(404, "note_not_found")
    return {"ok": True, "deleted": note_id}
