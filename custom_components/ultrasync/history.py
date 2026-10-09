"""ComNav history XML parsing and authenticated retrieval."""

import logging
import xml.etree.ElementTree as ET

import requests

_LOGGER = logging.getLogger(__name__)
LATEST_EVENT = 65535
OLDEST_EVENT = 65534


def parse_history_response(content):
    """Parse one history.xml response, preserving non-user event details."""
    root = ET.fromstring(content)
    raw = root.findtext("evrsp") or ""
    lines = [
        line.strip().rstrip("*").strip()
        for line in raw.splitlines()
        if line.strip()
    ]
    if not lines:
        return None
    action = lines[0]
    details = [
        line for line in lines[1:]
        if not line.startswith(("Time:", "Date:"))
    ]
    is_arm_event = action.casefold() in ("turn on", "turn off")
    return {
        "action": action,
        "area_name": details[0] if is_arm_event and details else "",
        "user": details[1] if is_arm_event and len(details) > 1 else "",
        "details": details,
        "timestamp": " ".join(
            line for line in lines[1:]
            if line.startswith(("Time:", "Date:"))
        ),
        "record": root.findtext("cur") or "",
        "oldest_record": root.findtext("old") or "",
        "latest_record": root.findtext("last") or "",
        "raw": raw.strip(),
    }


def fetch_history(hub, event=LATEST_EVENT):
    """Use the UltraSync library's session to read a ComNav history record.

    Called under the coordinator's hub_lock. Login is delegated to the library.
    """
    if not hub.session_id and not hub.login():
        return None
    url = hub.url.rstrip("/") + "/user/history.xml"
    for attempt in range(2):
        try:
            response = hub.session.post(
                url,
                data={"sess": hub.session_id, "event": event},
                auth=hub.auth,
                verify=hub.verify,
                timeout=hub.timeout,
                allow_redirects=False,
            )
            if response.status_code in (301, 302, 303, 307, 308, 401, 403):
                if attempt == 0 and hub.login():
                    continue
                return None
            response.raise_for_status()
            return parse_history_response(response.content)
        except (requests.RequestException, ET.ParseError, ValueError) as exc:
            _LOGGER.debug("ComNav history retrieval failed: %s", type(exc).__name__)
            return None
    return None


MAX_CATCHUP_EVENTS = 32


def collect_new_history(hub, previous_record=None, limit=MAX_CATCHUP_EVENTS):
    """Fetch recent events newest-first, stopping at the last seen record.

    On first poll, return the latest event as a baseline, not a backlog.
    History indexes are circular; never assume latest is numerically largest.
    """
    newest = fetch_history(hub, LATEST_EVENT)
    if newest is None:
        return None
    if previous_record is None or newest["record"] == previous_record:
        return [newest]

    records = [newest]
    visited = {newest["record"]}
    oldest = newest["oldest_record"]
    current = newest
    while len(records) < limit:
        if current["record"] == oldest:
            break
        try:
            previous_index = (int(current["record"]) - 1) % 65534
        except (ValueError, TypeError):
            break
        previous = fetch_history(hub, previous_index)
        if previous is None or previous["record"] in visited:
            break
        if previous["record"] == previous_record:
            break
        visited.add(previous["record"])
        records.append(previous)
        current = previous
    return list(reversed(records))
