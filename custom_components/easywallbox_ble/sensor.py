"""Readings exposed to Home Assistant."""

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entity import EasyWallboxEntity

FIELDS = [
    ("charge_state", "Estado", None, None, None),
    ("current_a", "Intensidad de carga", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    ("power_kw", "Potencia de carga", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    ("session_kwh", "Energía sesión", "kWh", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL),
    ("session_minutes", "Duración sesión", "min", None, SensorStateClass.MEASUREMENT),
    ("current_limit_a", "Límite confirmado", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    ("dpm_limit_a", "Límite DPM confirmado", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    ("dpm_house_kw", "Potencia vivienda DPM", "kW", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EasyWallboxSensor(coordinator, entry, field, name, unit, device_class, state_class)
        for field, name, unit, device_class, state_class in FIELDS
    ])


class EasyWallboxSensor(EasyWallboxEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, unit, device_class, state_class):
        super().__init__(coordinator, entry, key)
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class

    @property
    def native_value(self):
        return getattr(self.coordinator.data, self._key, None) if self.coordinator.data else None
