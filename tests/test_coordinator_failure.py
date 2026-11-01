"""Offline coordinator regression tests using Home Assistant's real update coordinator.

No panel credentials, network requests, service calls or HA runtime connection.
The production class body is loaded unmodified from the selected source file.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import timedelta
import logging
from pathlib import Path
import threading
import types
import unittest
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "custom_components/ultrasync/coordinator.py"
DISPATCHES = []


def load_production_class():
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(SOURCE))
    node = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "UltraSyncDataUpdateCoordinator")
    namespace = {
        "DataUpdateCoordinator": DataUpdateCoordinator,
        "UpdateFailed": UpdateFailed,
        "HomeAssistant": HomeAssistant,
        "timeout": asyncio.timeout,
        "timedelta": timedelta,
        "threading": threading,
        "ultrasync": types.SimpleNamespace(),
        "CONF_HOST": "host", "CONF_PIN": "pin", "CONF_USERNAME": "username",
        "CONF_SCAN_INTERVAL": "scan_interval",
        "DOMAIN": "ultrasync", "SENSOR_UPDATE_LISTENER": "ultrasync_update_sensors",
        "_LOGGER": logging.getLogger("ultrasync.offline_regression"),
        "async_dispatcher_send": lambda *args: DISPATCHES.append(args),
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["UltraSyncDataUpdateCoordinator"]


PRODUCTION_CLASS = load_production_class()


def snapshot():
    return {
        "areas": [{"bank": 0, "sequence": 1, "name": "Area 1", "status": "Ready", "arm_state": "disarm"}],
        "zones": [{"bank": x, "sequence": 1, "name": f"Zone {x + 1}", "status": "Ready"} for x in range(16)],
        "outputs": [{"name": "Output 1", "state": "0"}, {"name": "", "state": "0"}],
        "history_data": [{"area_name": "Area 1", "action": "Turn Off", "user": "Test", "timestamp": "2026-11-01T07:30:00"}],
    }


class CoordinatorRegression(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        DISPATCHES.clear()
        self.hass = HomeAssistant(str(ROOT / "runtime"))
        self.coordinator = PRODUCTION_CLASS.__new__(PRODUCTION_CLASS)
        DataUpdateCoordinator.__init__(
            self.coordinator, self.hass, logging.getLogger("ultrasync.offline_regression"),
            config_entry=None, name="ultrasync", update_interval=None,
        )
        self.coordinator.areas = []
        self.coordinator._init = False
        self.coordinator._area_delta = {}
        self.coordinator._zone_delta = {}
        self.coordinator._output_delta = {}
        self.coordinator._history_delta = {}
        self.coordinator._details = Mock(return_value=snapshot())
        self.entity = CoordinatorEntity(self.coordinator)

    async def asyncTearDown(self):
        await self.coordinator.async_shutdown()
        await self.hass.async_stop(force=True)

    async def test_complete_snapshot_exposes_all_twenty_values(self):
        await self.coordinator.async_refresh()
        self.assertTrue(self.coordinator.last_update_success)
        self.assertTrue(self.entity.available)
        self.assertEqual(len(self.coordinator.data), 20)
        self.assertEqual(self.coordinator.data["zone15_state"], "Ready")
        self.assertEqual(self.coordinator.data["zone16_state"], "Ready")
        self.assertEqual(self.coordinator.data["output2state"], "0")
        self.assertIn("history_nameArea 1state", self.coordinator.data)

    async def test_failed_first_poll_is_unavailable(self):
        self.coordinator._details.return_value = {}
        await self.coordinator.async_refresh()
        self.assertFalse(self.coordinator.last_update_success)
        self.assertFalse(self.entity.available)
        self.assertIsNone(self.coordinator.data)
        self.assertIsInstance(self.coordinator.last_exception, UpdateFailed)
        self.assertEqual(DISPATCHES, [])

    async def test_failed_poll_preserves_data_but_marks_unavailable(self):
        await self.coordinator.async_refresh()
        previous = deepcopy(self.coordinator.data)
        previous_areas = deepcopy(self.coordinator.areas)
        DISPATCHES.clear()
        self.coordinator._details.return_value = {}
        await self.coordinator.async_refresh()
        self.assertFalse(self.entity.available)
        self.assertEqual(self.coordinator.data, previous)
        self.assertEqual(self.coordinator.areas, previous_areas)
        self.assertEqual(DISPATCHES, [])

    async def test_failure_then_recovery_restores_available_current_data(self):
        await self.coordinator.async_refresh()
        self.coordinator._details.return_value = {}
        await self.coordinator.async_refresh()
        self.assertFalse(self.entity.available)
        recovered = snapshot()
        recovered["zones"][14].update(sequence=2, status="Not Ready")
        self.coordinator._details.return_value = recovered
        await self.coordinator.async_refresh()
        self.assertTrue(self.entity.available)
        self.assertTrue(self.coordinator.last_update_success)
        self.assertEqual(self.coordinator.data["zone15_state"], "Not Ready")

    async def test_absent_optional_outputs_history_are_valid(self):
        value = snapshot()
        value["outputs"] = []
        value["history_data"] = []
        self.coordinator._details.return_value = value
        await self.coordinator.async_refresh()
        self.assertTrue(self.entity.available)
        self.assertEqual(len(self.coordinator.data), 17)
        self.assertEqual(self.coordinator.data["area01_state"], "Ready")

    async def test_timeout_still_preserves_snapshot_and_marks_unavailable(self):
        await self.coordinator.async_refresh()
        previous = deepcopy(self.coordinator.data)
        self.coordinator._details.side_effect = TimeoutError
        await self.coordinator.async_refresh()
        self.assertFalse(self.entity.available)
        self.assertEqual(self.coordinator.data, previous)

    async def test_failure_does_not_modify_session_or_delta_tracking(self):
        await self.coordinator.async_refresh()
        before = (deepcopy(self.coordinator._zone_delta), deepcopy(self.coordinator._area_delta),
                  deepcopy(self.coordinator._output_delta), deepcopy(self.coordinator._history_delta))
        self.coordinator._details.return_value = {}
        await self.coordinator.async_refresh()
        after = (self.coordinator._zone_delta, self.coordinator._area_delta,
                 self.coordinator._output_delta, self.coordinator._history_delta)
        self.assertEqual(before, after)
        self.assertFalse(self.entity.available)


if __name__ == "__main__":
    unittest.main(verbosity=2)
