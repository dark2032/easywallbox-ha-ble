"""Tests that work WITHOUT Home Assistant, Bluetooth, or a physical charger."""

from pathlib import Path
import importlib.util
import unittest

module_path = Path(__file__).resolve().parents[1] / "custom_components/easywallbox_ble/frames.py"
spec = importlib.util.spec_from_file_location("easywallbox_protocol", module_path)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ProtocolTest(unittest.TestCase):
    def test_read_register(self):
        self.assertEqual(module.parse_eeprom("$EEP,READ,IDX,174,160", 174), 16.0)
        self.assertEqual(module.parse_eeprom("$EEP,READ,IDX,158,0", 158), 0.0)

    def test_user_current_write(self):
        self.assertEqual(module.write_current_command(16), "$EEP,WRITE,IDX,174,160")
        with self.assertRaises(ValueError):
            module.write_current_command(33)

    def test_ad_telemetry(self):
        p = ["0"] * 25
        p[:3] = ["$DATA", "READ", "AD"]
        p[7] = "8"
        p[9] = "1"
        p[10] = "160"
        p[11] = "3680"
        p[14] = "100"
        p[21] = "0"
        p[22] = "124"
        p[23] = "45"
        state = module.parse_ad(",".join(p), current_limit=16.0)
        self.assertTrue(state.charging)
        self.assertTrue(state.dpm_active)
        self.assertEqual(state.current_a, 16.0)
        self.assertEqual(state.power_kw, 3.68)
        self.assertEqual(state.session_kwh, 12.4)
        self.assertEqual(state.current_limit_a, 16.0)

    def test_truncated_message(self):
        with self.assertRaises(ValueError):
            module.parse_ad("$DATA,READ,AD,1")


if __name__ == "__main__":
    unittest.main()
