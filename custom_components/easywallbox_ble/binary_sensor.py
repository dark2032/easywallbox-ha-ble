"""Charging state, cable and DPM diagnostics."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entity import EasyWallboxEntity

FIELDS = [
    ("charging", "Cargando", BinarySensorDeviceClass.BATTERY_CHARGING),
    ("car_connected", "Vehículo conectado", BinarySensorDeviceClass.PLUG),
    ("dpm_active", "DPM activo", None),
    ("fault", "Avería", BinarySensorDeviceClass.PROBLEM),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EasyWallboxBinary(coordinator, entry, key, name, device_class)
        for key, name, device_class in FIELDS
    ] + [ConnectionBinary(coordinator, entry)])


class EasyWallboxBinary(EasyWallboxEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key, name, device_class):
        super().__init__(coordinator, entry, key)
        self._key = key
        self._attr_name = name
        self._attr_device_class = device_class

    @property
    def is_on(self):
        return getattr(self.coordinator.data, self._key, None) if self.coordinator.data else None


class ConnectionBinary(EasyWallboxEntity, BinarySensorEntity):
    """Reports whether the most recent polling cycle succeeded."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "connection")
        self._attr_name = "Comunicación reciente"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.last_update_success
