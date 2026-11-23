"""Simulate connection, pairing fallback, and authentication without HA hardware."""
import asyncio
import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


class SimClient:
    def __init__(self, correct_pin=True):
        self.services = SimpleNamespace(
            get_service=lambda uuid: object(),
            get_characteristic=lambda uuid: object(),
        )
        self.correct_pin = correct_pin
        self.is_connected = True
        self.notification_callback = None

    async def start_notify(self, uuid, callback):
        self.notification_callback = callback

    async def write_gatt_char(self, uuid, data):
        command = data.decode('ascii').strip()
        if command.startswith('$BLE,AUTH,'):
            reply = '$BLE,AUTH,OK' if self.correct_pin else '$BLE,AUTH,FAIL'
        else:
            reply = '$EEP,READ,IDX,174,160'
        self.notification_callback(uuid, bytearray((reply+'\n').encode('ascii')))

    async def disconnect(self):
        self.is_connected = False


class BleWithoutHardware(TestCase):
    def setUp(self):
        self.calls = []
        self.adapters = 1
        self.device = object()
        self.correct_pin = True
        self.fail_direct = False
        self.client = None
        fake_bluetooth = ModuleType('homeassistant.components.bluetooth')
        fake_bluetooth.async_scanner_count = lambda hass, connectable=True: self.adapters
        fake_bluetooth.async_ble_device_from_address = lambda hass, address, connectable=True: self.device
        fake_bluetooth.BluetoothScanningMode = SimpleNamespace(ACTIVE='active')
        async def scan(*args, **kwargs): return None
        fake_bluetooth.async_process_advertisements = scan
        self.fake_bluetooth = fake_bluetooth
        async def connect(cls, device, name, max_attempts=2, timeout=25.0, pair=False):
            self.calls.append(pair)
            if self.fail_direct and not pair: raise RuntimeError('BlueZ pairing required')
            self.client = SimClient(self.correct_pin)
            return self.client

        modules = {
            'bleak': ModuleType('bleak'),
            'bleak_retry_connector': ModuleType('bleak_retry_connector'),
            'homeassistant': ModuleType('homeassistant'),
            'homeassistant.components': ModuleType('homeassistant.components'),
            'homeassistant.components.bluetooth': fake_bluetooth,
            'homeassistant.core': ModuleType('homeassistant.core'),
        }
        modules['bleak'].BleakClient = object
        modules['bleak_retry_connector'].establish_connection = connect
        modules['homeassistant'].components = modules['homeassistant.components']
        modules['homeassistant.components'].bluetooth = fake_bluetooth
        modules['homeassistant.core'].HomeAssistant = object
        base = Path(__file__).resolve().parents[1] / 'custom_components/easywallbox_ble'
        package = ModuleType('easywallbox_test_package')
        package.__path__ = [str(base)]
        modules['easywallbox_test_package'] = package
        self.patcher = patch.dict(sys.modules, modules)
        self.patcher.start()
        self.mod = importlib.import_module('easywallbox_test_package.ble')
        self.diag = importlib.import_module('easywallbox_test_package.connection_diagnostics')
        self.sleep_patcher = patch.object(self.mod.asyncio, 'sleep', new=self._quick_sleep)
        self.sleep_patcher.start()

    async def _quick_sleep(self, delay): pass

    def tearDown(self):
        self.sleep_patcher.stop()
        self.patcher.stop()
        for name in list(sys.modules):
            if name.startswith('easywallbox_test_package'):
                del sys.modules[name]

    def test_success(self):
        ble = self.mod.EasyWallboxBle(object(), 'AA:BB:CC:DD:EE:FF', '1111', mode='direct')
        progress = self.diag.ConnectionProgress()
        res = asyncio.run(ble.async_probe(progress.ok))
        self.assertEqual(16.0, res)
        self.assertEqual(list(self.diag.STAGES), progress.passed)
        self.assertEqual([False], self.calls)
        self.assertFalse(self.client.is_connected)

    def test_no_adapter(self):
        self.adapters = 0
        ble = self.mod.EasyWallboxBle(object(), 'AA:BB:CC:DD:EE:FF', '1111')
        with self.assertRaises(self.diag.WallboxConnectionError) as cm:
            asyncio.run(ble.async_probe(lambda _: None))
        self.assertEqual('adapter', cm.exception.stage)
        self.assertEqual([], self.calls)

    def test_auth_fail_never_pairs_again(self):
        self.correct_pin = False
        ble = self.mod.EasyWallboxBle(object(), 'AA:BB:CC:DD:EE:FF', '1111', mode='auto')
        with self.assertRaises(self.diag.WallboxConnectionError) as cm:
            asyncio.run(ble.async_probe(lambda _: None))
        self.assertEqual('authentication', cm.exception.stage)
        self.assertEqual([False], self.calls)
        self.assertNotIn('1111', str(cm.exception))

    def test_auto_pairs_on_direct_connection_failure(self):
        self.fail_direct = True
        ble = self.mod.EasyWallboxBle(object(), 'AA:BB:CC:DD:EE:FF', '1111', mode='auto')
        res = asyncio.run(ble.async_probe(lambda _: None))
        self.assertEqual(16.0, res)
        self.assertEqual([False, True], self.calls)


if __name__ == '__main__':
    import unittest
    unittest.main()
