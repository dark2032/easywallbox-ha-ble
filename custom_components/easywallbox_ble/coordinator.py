"""Poll the charger and publish confirmed values to Home Assistant."""

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ble import EasyWallboxBle
from .const import POLL_SECONDS
from .frames import WallboxState

LOGGER = logging.getLogger(__name__)


class EasyWallboxCoordinator(DataUpdateCoordinator[WallboxState]):
    def __init__(self, hass, ble: EasyWallboxBle, max_amps: int):
        super().__init__(
            hass, LOGGER, name="easyWallbox BLE", update_interval=timedelta(seconds=POLL_SECONDS)
        )
        self.ble = ble
        self.max_amps = max_amps

    async def _async_update_data(self) -> WallboxState:
        try:
            return await self.ble.async_read()
        except Exception as err:
            raise UpdateFailed(f"Could not poll easyWallbox: {err}") from err

    async def async_set_current(self, value: int):
        if value < 6 or value > self.max_amps:
            raise ValueError(f"Configured upper limit is {self.max_amps} A")
        await self.ble.async_write_current(value)
        await self.async_request_refresh()
