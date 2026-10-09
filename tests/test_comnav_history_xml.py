"""Regression tests for the Home Assistant ComNav history parser."""

from custom_components.ultrasync.history import (
    LATEST_EVENT,
    OLDEST_EVENT,
    parse_history_response,
)


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
