"""Regression tests for the Home Assistant ComNav history parser."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "comnav_history", Path(__file__).resolve().parents[1] / "custom_components" / "ultrasync" / "history.py"
)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)
LATEST_EVENT = history.LATEST_EVENT
OLDEST_EVENT = history.OLDEST_EVENT
parse_history_response = history.parse_history_response


def test_navigation_commands():
    assert LATEST_EVENT == 65535
    assert OLDEST_EVENT == 65534


def test_disarm_user():
    event = parse_history_response(b"""<response><evrsp>Turn Off
Aussie Fencing
HomeAssistant
Time: 05:46
Date: 9 Oct</evrsp><cur>173</cur><old>175</old><last>174</last></response>""")
    assert event["action"] == "Turn Off"
    assert event["area_name"] == "Aussie Fencing"
    assert event["user"] == "HomeAssistant"
    assert event["record"] == "173"


def test_device_event_is_not_a_user():
    event = parse_history_response(b"""<response><evrsp>Communication Failed*
Device 191
Time: 05:49
Date: 9 Oct</evrsp><cur>174</cur><old>175</old><last>174</last></response>""")
    assert event["action"] == "Communication Failed"
    assert event["user"] == ""
    assert event["details"] == ["Device 191"]
    assert event["latest_record"] == "174"


def test_physical_keypad_disarm():
    event = parse_history_response(b"""<response><evrsp>Turn Off
Aussie Fencing
Cleaners
Time: 08:48
Date: 3 Oct</evrsp><cur>120</cur><old>175</old><last>174</last></response>""")
    assert event["action"] == "Turn Off"
    assert event["area_name"] == "Aussie Fencing"
    assert event["user"] == "Cleaners"
    assert event["record"] == "120"


def test_catchup_skips_intermediate_communication_fault(monkeypatch):

    events = {
        history.LATEST_EVENT: {"record": "174", "oldest_record": "175", "action": "Communication Failed"},
        173: {"record": "173", "oldest_record": "175", "action": "Turn Off", "user": "Cleaners"},
        172: {"record": "172", "oldest_record": "175", "action": "Turn On", "user": "HomeAssistant"},
    }
    monkeypatch.setattr(history, "fetch_history", lambda hub, event: events.get(event))
    result = history.collect_new_history(None, previous_record="172")
    assert [item["record"] for item in result] == ["173", "174"]
    assert result[0]["user"] == "Cleaners"


def test_first_poll_does_not_replay_backlog(monkeypatch):
    from custom_components.ultrasync import history

    calls = []
    def fake_fetch(hub, event):
        calls.append(event)
        return {"record": "174", "oldest_record": "175"}
    monkeypatch.setattr(history, "fetch_history", fake_fetch)
    assert len(history.collect_new_history(None)) == 1
    assert calls == [history.LATEST_EVENT]
