"""ComNav history response parsing utilities."""

import xml.etree.ElementTree as ET


def parse_history_response(content):
    """Parse the history.xml response into structured event details."""
    root = ET.fromstring(content)
    lines = [line.strip().rstrip('*').strip() for line in (root.findtext('evrsp') or '').splitlines() if line.strip()]
    if not lines:
        return None
    return {
        'action': lines[0],
        'area_name': lines[1] if len(lines) > 1 else '',
        'user': next((line for line in lines[2:] if not line.startswith(('Time:', 'Date:'))), ''),
        'timestamp': ' '.join(line for line in lines if line.startswith(('Time:', 'Date:'))),
        'record': root.findtext('cur') or '',
    }
