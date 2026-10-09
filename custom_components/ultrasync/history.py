"""ComNav history XML parsing utilities."""

import xml.etree.ElementTree as ET

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
