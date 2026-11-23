"""Manual setup while automatic BLE discovery is not validated."""

import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS

from .const import CONF_AUTH_PIN, CONF_MAX_AMPS, DOMAIN

MAC_PATTERN = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


class EasyWallboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            pin = user_input[CONF_AUTH_PIN].strip()
            max_amps = user_input[CONF_MAX_AMPS]
            if not MAC_PATTERN.fullmatch(address):
                errors[CONF_ADDRESS] = "invalid_address"
            elif not pin.isdigit() or not 4 <= len(pin) <= 6:
                errors[CONF_AUTH_PIN] = "invalid_pin"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"easyWallbox {address[-5:]}",
                    data={CONF_ADDRESS: address, CONF_AUTH_PIN: pin,
                          CONF_MAX_AMPS: max_amps},
                )

        schema = vol.Schema({
            vol.Required(CONF_ADDRESS): str,
            vol.Required(CONF_AUTH_PIN): str,
            vol.Required(CONF_MAX_AMPS, default=16): vol.All(
                vol.Coerce(int), vol.Range(min=6, max=32)
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
