"""Support for Docker switches."""
import logging
from typing import Any, Dict

from homeassistant.core import callback
from homeassistant.const import CONF_NAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.switch import SwitchDevice

from .const import (
    DOMAIN,
    CONF_CONTAINERS,
    DATA_HOST,
    DATA_VERSION_INFO,
    DATA_UPDATED,
    DOCKER_CLIENT
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Docker Switch."""

    switches = [ContainerSwitch(
        hass = hass, 
        api = hass.data[DOCKER_CLIENT][DATA_HOST], 
        clientname = config_entry.data[CONF_NAME], 
        container_name = container
    ) for container in hass.data[DOCKER_CLIENT][CONF_CONTAINERS]]

    if switches:
        async_add_entities(switches, True)
    else:
        _LOGGER.info("No containers setup")
        return False

class ContainerSwitch(SwitchDevice):
    def __init__(self, hass, api, clientname, container_name):
        self._hass = hass
        self._api = api
        self._clientname = clientname
        self._container_name = container_name
        self._state = False
        self._container = api.get_container(container_name)
        self._unsub_update = None
        self._attributes = self._container.get_info()

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return "docker_{}_{}".format(self._clientname, self._container_name)

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Docker {} {}".format(self._clientname, self._container_name)

    @property
    def icon(self):
        return 'mdi:docker'

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        self._unsub_update = async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    async def async_update(self) -> None:
        self._state = self._container.get_state()

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this Docker host instance."""
        return {
            "identifiers": {
                (DOMAIN, self._clientname, self._container_name)
            },
            "name": "{}_{}".format(self._clientname, self._container_name),
            "manufacturer": "Docker",
            "model": "Container",
            "sw_version": self.hass.data[DOCKER_CLIENT][DATA_VERSION_INFO]["version"]
        }

    @property
    def is_on(self):
        return self._state

    def turn_on(self, **kwargs) -> None:
        """Turn off the switch."""
        self._container.start()

    def turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        self._container.stop()
