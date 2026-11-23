"""Direct BLE integration, initial safe read-only UI."""

from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .ble import EasyWallboxBle
from .const import CONF_AUTH_PIN, CONF_CONNECTION_MODE, CONF_MAX_AMPS, DOMAIN
from .coordinator import EasyWallboxCoordinator

# Deliberately avoid exposing write controls until real hardware validation.
PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ble = EasyWallboxBle(
        hass, entry.data[CONF_ADDRESS], entry.data[CONF_AUTH_PIN],
        mode=entry.data.get(CONF_CONNECTION_MODE, "auto"),
    )
    coordinator = EasyWallboxCoordinator(hass, ble, entry.data[CONF_MAX_AMPS])
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    success = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if success:
        hass.data[DOMAIN].pop(entry.entry_id)
    return success
