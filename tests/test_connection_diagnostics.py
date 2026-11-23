"""Pure Python test: diagnostic text must not expose PINs."""
import importlib.util
from pathlib import Path
import unittest
import sys

path = Path(__file__).resolve().parents[1] / "custom_components/easywallbox_ble/connection_diagnostics.py"
spec = importlib.util.spec_from_file_location("wallbox_diagnostics", path)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_initial(self):
        self.assertIn("Pendiente", mod.ConnectionProgress().as_text())

    def test_failed_stage(self):
        r = mod.ConnectionProgress()
        r.ok("adapter")
        r.ok("discovery")
        r.fail(mod.WallboxConnectionError("connection", "Conexión denegada"))
        s = r.as_text()
        self.assertIn("✓ Adaptador", s)
        self.assertIn("✗ Conexión BLE", s)
        self.assertNotIn("Autorización A:", s)

    def test_success(self):
        r = mod.ConnectionProgress()
        for stage in mod.STAGES: r.ok(stage)
        self.assertIn("✓ Lectura de prueba", r.as_text())
