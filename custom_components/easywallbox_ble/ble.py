"""Experimental BLE client, explicit stages and read-only connection probe.

The wallbox normally permits only one central; short sessions reduce conflicts.
The code NEVER removes an OS bond or alters DPM. A: application authorization
and P: Bluetooth OS pairing are two different secrets.
"""

import asyncio
import logging
from collections.abc import Callable

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .connection_diagnostics import WallboxConnectionError
from .const import RX_UUID, SERVICE_UUID, TX_UUID
from .frames import WallboxState, parse_ad, parse_eeprom, write_current_command

_LOGGER = logging.getLogger(__name__)
CONNECTION_MODES = ("auto", "direct", "pair")


class EasyWallboxBle:
    def __init__(self, hass: HomeAssistant, address: str, auth_pin: str,
                 mode: str = "auto"):
        self.hass = hass
        self.address = address
        self._auth_pin = auth_pin
        self.mode = mode if mode in CONNECTION_MODES else "auto"
        self._lock = asyncio.Lock()
        self._buffer = bytearray()
        self._pending: asyncio.Future[str] | None = None
        self._expected: str | None = None

    def _notification(self, _sender, data: bytearray) -> None:
        self._buffer.extend(data)
        if len(self._buffer) > 4096:
            self._buffer.clear()
            _LOGGER.warning("easyWallbox BLE buffer overflow")
            return
        while b"\n" in self._buffer:
            raw_line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            line = raw_line.decode("ascii", errors="replace").rstrip("\r")
            # Do not log AUTH commands, secrets, or complete BLE payloads.
            future = self._pending
            if future is None or future.done():
                continue
            if line.startswith("$BLE,AUTH,FAIL"):
                future.set_exception(PermissionError("PIN A: rechazado por el cargador"))
            elif line.startswith(("$ERR,", "$EEP,WRITE,FAIL")):
                future.set_exception(RuntimeError("El cargador rechazó el comando"))
            elif self._expected and line.startswith(self._expected):
                future.set_result(line)

    async def _command(self, client: BleakClient, command: str, expected: str) -> str:
        if self._pending and not self._pending.done():
            raise RuntimeError("Concurrent BLE request")
        self._pending = asyncio.get_running_loop().create_future()
        self._expected = expected
        try:
            await client.write_gatt_char(TX_UUID, (command + "\n").encode("ascii"))
            return await asyncio.wait_for(self._pending, timeout=10.0)
        finally:
            self._pending = None
            self._expected = None

    async def _find_device(self, on_stage: Callable[[str], None]):
        if bluetooth.async_scanner_count(self.hass, connectable=True) <= 0:
            raise WallboxConnectionError(
                "adapter", "Home Assistant no tiene un escáner BLE capaz de conectar."
            )
        on_stage("adapter")
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            # HA owns the scanner; never run a parallel BleakScanner.
            try:
                await bluetooth.async_process_advertisements(
                    self.hass, lambda info: info.address.upper() == self.address,
                    {"address": self.address, "connectable": True},
                    bluetooth.BluetoothScanningMode.ACTIVE, timeout=12,
                )
            except TimeoutError:
                pass
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
        if device is None:
            raise WallboxConnectionError(
                "discovery", "No aparece la MAC indicada. Acércate, revisa la MAC y cierra la app oficial."
            )
        on_stage("discovery")
        return device

    async def _once(self, device, transaction, on_stage, pair: bool):
        client = None
        try:
            try:
                client = await establish_connection(
                    BleakClient, device, f"easyWallbox {self.address}",
                    max_attempts=2, timeout=25.0, pair=pair,
                )
            except Exception as exc:
                _LOGGER.debug("BLE connection method=%s failed (%s)",
                              "pair" if pair else "direct", type(exc).__name__)
                raise WallboxConnectionError(
                    "connection", "No se pudo conectar ni completar el emparejamiento del sistema."
                    if pair else "No se pudo abrir el enlace Bluetooth."
                ) from exc
            on_stage("connection")
            try:
                # Discover service before writing any data to an unknown BLE device.
                service = client.services.get_service(SERVICE_UUID)
                if not service or not client.services.get_characteristic(RX_UUID) \
                   or not client.services.get_characteristic(TX_UUID):
                    raise WallboxConnectionError(
                        "service", "El dispositivo no anuncia las características GATT de easyWallbox."
                    )
                on_stage("service")
                await client.start_notify(RX_UUID, self._notification)
            except WallboxConnectionError:
                raise
            except Exception as exc:
                raise WallboxConnectionError(
                    "service", "No se pueden activar las notificaciones GATT; podría faltar emparejamiento P:."
                ) from exc
            # The reference ESPHome implementation waits for BLE encryption
            # / peripheral initialization before sending the AUTH command.
            await asyncio.sleep(8)
            try:
                auth = await self._command(
                    client, f"$BLE,AUTH,{self._auth_pin}", "$BLE,AUTH,OK"
                )
                if not auth.startswith("$BLE,AUTH,OK"):
                    raise PermissionError("unexpected authorization response")
            except PermissionError as exc:
                raise WallboxConnectionError(
                    "authentication", "El cargador rechazó el PIN A:."
                ) from exc
            except (TimeoutError, Exception) as exc:
                # The callback raises PermissionError for explicit AUTH FAIL,
                # otherwise an auth timeout may indicate missing BLE bond.
                raise WallboxConnectionError(
                    "authentication", "No hubo respuesta AUTH; posible emparejamiento P: pendiente."
                ) from exc
            on_stage("authentication")
            try:
                result = await transaction(client)
            except Exception as exc:
                raise WallboxConnectionError(
                    "reading", "La autorización funcionó pero no se pudo leer el cargador."
                ) from exc
            on_stage("reading")
            return result
        finally:
            if client is not None:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except Exception:
                    _LOGGER.debug("Disconnection failed", exc_info=True)

    async def _session(self, transaction, on_stage=None):
        on_stage = on_stage or (lambda stage: None)
        async with self._lock:
            device = await self._find_device(on_stage)
            self._buffer.clear()
            methods = (False, True) if self.mode == "auto" else (self.mode == "pair",)
            for pair in methods:
                try:
                    return await self._once(device, transaction, on_stage, pair)
                except WallboxConnectionError as exc:
                    # Never retry wrong A: PIN, an unknown device, or a bad
                    # confirmed protocol read with another pairing method.
                    should_pair = (
                        self.mode == "auto" and not pair
                        and exc.stage in {"connection", "service"}
                        or self.mode == "auto" and not pair
                        and exc.stage == "authentication"
                        and "No hubo respuesta" in exc.reason
                    )
                    if not should_pair:
                        raise
                    _LOGGER.info("Direct BLE failed at %s; trying OS pairing", exc.stage)
                    self._buffer.clear()
            raise WallboxConnectionError("connection", "Fallaron ambos métodos BLE")

    async def async_probe(self, on_stage: Callable[[str], None]) -> float:
        """Non-mutating end-to-end test; no change in charging parameters."""
        async def read_once(client):
            reply = await self._command(
                client, "$EEP,READ,IDX,174", "$EEP,READ,IDX,174,"
            )
            return parse_eeprom(reply, 174)
        return await self._session(read_once, on_stage)

    async def async_read(self) -> WallboxState:
        async def transaction(client):
            current_reply = await self._command(
                client, "$EEP,READ,IDX,174", "$EEP,READ,IDX,174,"
            )
            dpm_reply = await self._command(
                client, "$EEP,READ,IDX,158", "$EEP,READ,IDX,158,"
            )
            ad = await self._command(client, "$DATA,READ,AD", "$DATA,READ,AD,")
            return parse_ad(
                ad, current_limit=parse_eeprom(current_reply, 174),
                dpm_limit=parse_eeprom(dpm_reply, 158),
            )
        return await self._session(transaction)

    async def async_write_current(self, amps: int) -> float:
        """Existing code retained but intentionally not exposed in v0.1.1 UI."""
        command = write_current_command(amps)
        async def transaction(client):
            try:
                await self._command(client, command, "$EEP,WRITE,IDX,174,")
            except TimeoutError:
                _LOGGER.warning("No write acknowledgement: verifying value")
            reply = await self._command(client, "$EEP,READ,IDX,174", "$EEP,READ,IDX,174,")
            confirmed = parse_eeprom(reply, 174)
            if abs(confirmed - amps) > 0.1:
                raise ValueError("Current limit not confirmed")
            return confirmed
        return await self._session(transaction)
