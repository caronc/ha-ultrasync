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
Example Office
Automation User
Time: 05:46
Date: 9 Oct</evrsp><cur>173</cur><old>175</old><last>174</last></response>""")
    assert event["action"] == "Turn Off"
    assert event["area_name"] == "Example Office"
    assert event["user"] == "Automation User"
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
Example Office
Keypad User
Time: 08:48
Date: 3 Oct</evrsp><cur>120</cur><old>175</old><last>174</last></response>""")
    assert event["action"] == "Turn Off"
    assert event["area_name"] == "Example Office"
    assert event["user"] == "Keypad User"
    assert event["record"] == "120"


def test_catchup_skips_intermediate_communication_fault(monkeypatch):

    events = {
        history.LATEST_EVENT: {"record": "174", "oldest_record": "175", "action": "Communication Failed"},
        173: {"record": "173", "oldest_record": "175", "action": "Turn Off", "user": "Keypad User"},
        172: {"record": "172", "oldest_record": "175", "action": "Turn On", "user": "Automation User"},
    }
    monkeypatch.setattr(history, "fetch_history", lambda hub, event: events.get(event))
    result = history.collect_new_history(None, previous_record="172")
    assert [item["record"] for item in result] == ["173", "174"]
    assert result[0]["user"] == "Keypad User"


def test_first_poll_does_not_replay_backlog(monkeypatch):

    calls = []
    def fake_fetch(hub, event):
        calls.append(event)
        return {"record": "174", "oldest_record": "175"}
    monkeypatch.setattr(history, "fetch_history", fake_fetch)
    assert len(history.collect_new_history(None)) == 1
    assert calls == [history.LATEST_EVENT]


def test_bootstrap_finds_last_known_users_without_confusing_device_events(monkeypatch):
    events = {
        history.LATEST_EVENT: {"record": "174", "oldest_record": "175",
                               "action": "Communication Failed", "user": ""},
        173: {"record": "173", "oldest_record": "175",
              "action": "Turn Off", "user": "Keypad User"},
        172: {"record": "172", "oldest_record": "175",
              "action": "Communication Failed", "user": ""},
        171: {"record": "171", "oldest_record": "175",
              "action": "Turn On", "user": "Another User"},
    }
    monkeypatch.setattr(history, "fetch_history", lambda hub, event: events.get(event))
    latest, users = history.bootstrap_history(None)
    assert latest["record"] == "174"
    assert users["turn off"]["user"] == "Keypad User"
    assert users["turn on"]["user"] == "Another User"
