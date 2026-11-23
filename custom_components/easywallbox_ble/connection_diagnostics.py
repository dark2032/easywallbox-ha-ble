"""Presentation-only diagnostics, without any Home Assistant dependency."""

from dataclasses import dataclass, field

STAGES = ("adapter", "discovery", "connection", "service", "authentication", "reading")
LABELS = {
    "adapter": "Adaptador Bluetooth",
    "discovery": "Detección del dispositivo",
    "connection": "Conexión BLE",
    "service": "Servicio del cargador",
    "authentication": "Autorización A:",
    "reading": "Lectura de prueba",
}

class WallboxConnectionError(ConnectionError):
    """A predictable failure with no sensitive PIN or BLE payload."""

    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason

@dataclass
class ConnectionProgress:
    passed: list[str] = field(default_factory=list)
    failure: WallboxConnectionError | None = None

    def ok(self, stage: str) -> None:
        if stage in STAGES and stage not in self.passed:
            self.passed.append(stage)

    def fail(self, error: WallboxConnectionError) -> None:
        self.failure = error

    def as_text(self) -> str:
        """Status shown to the installer in the HA config form."""
        if not self.passed and not self.failure:
            return "Pendiente de iniciar comprobaciones."
        result = []
        for stage in STAGES:
            if stage in self.passed:
                result.append(f"✓ {LABELS[stage]}")
            elif self.failure and stage == self.failure.stage:
                result.append(f"✗ {LABELS[stage]}: {self.failure.reason}")
                break
            else:
                result.append(f"· {LABELS[stage]}: no comprobado")
                break
        return " | ".join(result)
