"""Common device identity for all wallbox entities."""

from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class EasyWallboxEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_ADDRESS])},
            "name": "Free2move easyWallbox",
            "manufacturer": "eSolutions / Free2move",
            "model": "easyWallbox",
        }
