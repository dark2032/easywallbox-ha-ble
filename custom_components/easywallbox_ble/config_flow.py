"""Connection-first configuration: BT adapter, detection, GATT, A: PIN, read."""

import logging
import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers import selector

from .ble import EasyWallboxBle
from .connection_diagnostics import ConnectionProgress, WallboxConnectionError
from .const import CONF_AUTH_PIN, CONF_CONNECTION_MODE, CONF_DISCOVERED_DEVICE, CONF_MAX_AMPS, DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)
MAC_PATTERN = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


class EasyWallboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _devices(self):
        """Use HA's shared BLE discovery data; no secondary BLE scan."""
        result = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            addr = info.address.upper()
            name = info.name or "Dispositivo BLE"
            if SERVICE_UUID.lower() in (uuid.lower() for uuid in (info.service_uuids or ())) or "wallbox" in name.lower():
                result[addr] = f"{name} ({addr}) [candidato easyWallbox]"
            elif len(result) < 15:
                result[addr] = f"{name} ({addr})"
        return result

    async def async_step_user(self, user_input=None):
        errors = {}
        progress = ConnectionProgress()
        self._last_report = getattr(self, "_last_report", None)
        if user_input is None and bluetooth.async_scanner_count(self.hass, connectable=True):
            try:
                await bluetooth.async_request_active_scan(self.hass, duration=5)
            except Exception:
                _LOGGER.debug("Initial Bluetooth discovery sweep failed", exc_info=True)
        devices = self._devices()
        if user_input is not None:
            choice = user_input.get(CONF_DISCOVERED_DEVICE, "manual")
            address = (choice if choice != "manual" else
                       user_input.get(CONF_ADDRESS, "").strip().upper())
            pin = user_input[CONF_AUTH_PIN].strip()
            max_amps = user_input[CONF_MAX_AMPS]
            mode = user_input[CONF_CONNECTION_MODE]
            if not MAC_PATTERN.fullmatch(address):
                errors["base"] = "invalid_address"
            elif not pin.isdigit() or not 4 <= len(pin) <= 6:
                errors["base"] = "invalid_pin"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                ble = EasyWallboxBle(self.hass, address, pin, mode=mode)
                try:
                    await ble.async_probe(progress.ok)
                except WallboxConnectionError as exc:
                    progress.fail(exc)
                    _LOGGER.warning("Connection test %s: %s", exc.stage, exc.reason)
                    errors["base"] = {
                        "adapter": "no_adapter",
                        "discovery": "not_found",
                        "connection": "connection_failed",
                        "service": "service_failed",
                        "authentication": "auth_failed",
                        "reading": "read_failed",
                    }.get(exc.stage, "connection_failed")
                except Exception:
                    _LOGGER.exception("Unexpected BLE configuration failure")
                    errors["base"] = "unexpected"
                else:
                    return self.async_create_entry(
                        title=f"easyWallbox {address[-5:]}",
                        data={
                            CONF_ADDRESS: address, CONF_AUTH_PIN: pin,
                            CONF_CONNECTION_MODE: mode, CONF_MAX_AMPS: max_amps,
                        },
                    )
                self._last_report = progress.as_text()

        # Show status *before* trying a PIN too. Passive-only adapters do
        # not qualify because the wallbox needs an outgoing connection.
        scanner_count = bluetooth.async_scanner_count(self.hass, connectable=True)
        if scanner_count == 0 and not errors:
            errors["base"] = "no_adapter"
        info = (f"Escáneres con conexión: {scanner_count}. "
                f"Dispositivos BLE visibles: {len(devices)}. "
                f"{self._last_report or 'Aún no se ha ejecutado la prueba.'}")
        options = {"manual": "Introducir MAC manualmente", **devices}
        schema = vol.Schema({
            vol.Required(CONF_DISCOVERED_DEVICE, default=user_input.get(CONF_DISCOVERED_DEVICE, "manual") if user_input else "manual"): vol.In(options),
            vol.Optional(CONF_ADDRESS, default=user_input.get(CONF_ADDRESS, "") if user_input else ""): str,
            vol.Required(CONF_AUTH_PIN): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_CONNECTION_MODE, default=user_input.get(CONF_CONNECTION_MODE, "auto") if user_input else "auto"): vol.In({
                "auto": "Automático (directo y luego emparejar si falla)",
                "direct": "Directo (sin solicitar emparejamiento OS)",
                "pair": "Solicitar emparejamiento al sistema operativo",
            }),
            vol.Required(CONF_MAX_AMPS, default=user_input.get(CONF_MAX_AMPS, 16) if user_input else 16): vol.All(vol.Coerce(int), vol.Range(min=6, max=32)),
        })
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors,
            description_placeholders={"diagnostic": info},
        )
