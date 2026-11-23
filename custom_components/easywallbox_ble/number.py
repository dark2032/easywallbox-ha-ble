"""Change the charger user limit, never the DPM safety limit."""

from homeassistant.components.number import NumberEntity, NumberMode, NumberDeviceClass
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .entity import EasyWallboxEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EasyWallboxCurrentLimit(coordinator, entry)])


class EasyWallboxCurrentLimit(EasyWallboxEntity, NumberEntity):
    _attr_name = "Intensidad máxima"
    _attr_native_min_value = 6
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "A"
    _attr_mode = NumberMode.SLIDER
    _attr_device_class = NumberDeviceClass.CURRENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "set_current")
        self._attr_native_max_value = coordinator.max_amps

    @property
    def native_value(self):
        return self.coordinator.data.current_limit_a if self.coordinator.data else None

    async def async_set_native_value(self, value: float):
        if not float(value).is_integer():
            raise HomeAssistantError("Use an integer current in amperes")
        try:
            await self.coordinator.async_set_current(int(value))
        except Exception as err:
            raise HomeAssistantError(f"Could not set easyWallbox current: {err}") from err
