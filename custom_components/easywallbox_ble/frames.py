"""Pure protocol parsing, independent of Home Assistant.

Field mappings adapted from publicly documented eSolutions EasyWallbox
ESPHome reverse engineering by paolofaz (MIT-licensed project).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WallboxState:
    charge_state: str
    charging: bool
    car_connected: bool
    dpm_active: bool
    fault: bool
    current_a: float
    power_kw: float
    session_kwh: float
    session_minutes: int
    dpm_house_kw: float
    current_limit_a: float | None = None
    dpm_limit_a: float | None = None


CHARGE_STATES = {
    3: "Desconectado",
    5: "Pausado",
    6: "Vehículo preparado",
    8: "Cargando",
    12: "Error",
}


def parse_eeprom(line: str, index: int) -> float:
    """Parse a reply value, stored in tenths of an ampere."""
    parts = line.strip().split(",")
    if (
        len(parts) < 5
        or parts[0] != "$EEP"
        or parts[1] not in ("READ", "WRITE")
        or parts[2] != "IDX"
        or parts[3] != str(index)
    ):
        raise ValueError(f"Unexpected EEPROM reply for index {index}")
    return int(parts[4]) / 10.0


def parse_ad(line: str, *, current_limit: float | None = None,
             dpm_limit: float | None = None) -> WallboxState:
    """Decode the AD telemetry reported by a compatible easyWallbox.

    The values and their units follow paolofaz's firmware. These must be
    checked against real hardware before being treated as validated.
    """
    parts = line.strip().split(",")
    if len(parts) < 25 or parts[:3] != ["$DATA", "READ", "AD"]:
        raise ValueError("Unexpected or truncated AD telemetry")
    state = int(parts[7])
    return WallboxState(
        charge_state=CHARGE_STATES.get(state, f"Desconocido ({state})"),
        charging=state == 8,
        car_connected=state in (5, 6, 8),
        dpm_active=int(parts[9]) == 1,
        fault=int(parts[21]) != 0,
        current_a=int(parts[10]) / 10.0,
        power_kw=int(parts[11]) / 1000.0,
        session_kwh=int(parts[22]) / 10.0,
        session_minutes=int(parts[23]),
        dpm_house_kw=int(parts[14]) * 0.023,
        current_limit_a=current_limit,
        dpm_limit_a=dpm_limit,
    )


def write_current_command(amps: int) -> str:
    """Write user current limit (EEPROM index 174), not DPM (index 158)."""
    if not 6 <= amps <= 32:
        raise ValueError("The requested current must be between 6 and 32 A")
    return f"$EEP,WRITE,IDX,174,{amps * 10}"
