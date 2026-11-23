"""Temporary BLE connection per transaction.

The wallbox reportedly accepts only one BLE controller. We disconnect after
polling to coexist as much as possible with the manufacturer's application.
"""

import asyncio
import logging
from collections.abc import Callable

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import RX_UUID, TX_UUID
from .frames import WallboxState, parse_ad, parse_eeprom, write_current_command

_LOGGER = logging.getLogger(__name__)


class EasyWallboxBle:
    def __init__(self, hass: HomeAssistant, address: str, auth_pin: str):
        self.hass = hass
        self.address = address
        self._auth_pin = auth_pin
        self._lock = asyncio.Lock()
        self._buffer = bytearray()
        self._pending: asyncio.Future[str] | None = None
        self._expected: str | None = None

    def _notification(self, _sender, data: bytearray):
        self._buffer.extend(data)
        if len(self._buffer) > 4096:
            self._buffer.clear()
            _LOGGER.warning("easyWallbox: truncated BLE stream")
            return
        while b"\n" in self._buffer:
            raw_line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            line = raw_line.decode("ascii", errors="replace").rstrip("\r")
            # Never log the authorization payload or password.
            _LOGGER.debug("easyWallbox reply type: %s", line.split(",", 2)[:2])
            future = self._pending
            if future is None or future.done():
                continue
            if line.startswith(("$ERR,", "$BLE,AUTH,FAIL", "$EEP,WRITE,FAIL")):
                future.set_exception(RuntimeError("Wallbox rejected BLE command"))
            elif self._expected and line.startswith(self._expected):
                future.set_result(line)

    async def _command(self, client: BleakClient, command: str, expected: str) -> str:
        if self._pending and not self._pending.done():
            raise RuntimeError("Concurrent BLE request")
        loop = asyncio.get_running_loop()
        self._pending = loop.create_future()
        self._expected = expected
        try:
            await client.write_gatt_char(TX_UUID, (command + "\n").encode("ascii"))
            return await asyncio.wait_for(self._pending, 10.0)
        finally:
            self._pending = None
            self._expected = None

    async def _session(self, transaction: Callable[[BleakClient], object]):
        async with self._lock:
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if device is None:
                raise ConnectionError(
                    "Wallbox not discovered by a connectable Home Assistant BLE adapter"
                )
            self._buffer.clear()
            # Bluetooth bonding/passkey is not handled here. The OS Bluetooth
            # adapter must already have a valid bond if the device requires it.
            client = await establish_connection(
                BleakClient, device, f"easyWallbox {self.address}"
            )
            try:
                await client.start_notify(RX_UUID, self._notification)
                reply = await self._command(
                    client, f"$BLE,AUTH,{self._auth_pin}", "$BLE,AUTH,OK"
                )
                if reply != "$BLE,AUTH,OK":
                    raise PermissionError("easyWallbox authorization failed")
                return await transaction(client)
            finally:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except Exception:
                    _LOGGER.debug("BLE disconnect failed", exc_info=True)

    async def async_read(self) -> WallboxState:
        async def transaction(client):
            user_reply = await self._command(
                client, "$EEP,READ,IDX,174", "$EEP,READ,IDX,174,"
            )
            dpm_reply = await self._command(
                client, "$EEP,READ,IDX,158", "$EEP,READ,IDX,158,"
            )
            ad_reply = await self._command(client, "$DATA,READ,AD", "$DATA,READ,AD,")
            return parse_ad(
                ad_reply,
                current_limit=parse_eeprom(user_reply, 174),
                dpm_limit=parse_eeprom(dpm_reply, 158),
            )
        return await self._session(transaction)

    async def async_write_current(self, amps: int) -> float:
        command = write_current_command(amps)
        async def transaction(client):
            # Send just once. If acknowledgement is absent, read register to
            # verify; never blindly repeat a potentially applied write.
            try:
                await self._command(client, command, "$EEP,WRITE,IDX,174,")
            except TimeoutError:
                _LOGGER.warning("No write acknowledgement; verifying current limit")
            reply = await self._command(
                client, "$EEP,READ,IDX,174", "$EEP,READ,IDX,174,"
            )
            confirmed = parse_eeprom(reply, 174)
            if abs(confirmed - amps) > 0.1:
                raise RuntimeError(f"Requested {amps} A but confirmed {confirmed} A")
            return confirmed
        return await self._session(transaction)
