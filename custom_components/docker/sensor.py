"""Support for Docker sensors."""
import logging
from typing import Any, Dict

from . import DockerContainer
from .const import (
    DOMAIN,
    DOCKER_CLIENT,
    DATA_HOST,
    DATA_VERSION_INFO,
    DATA_UPDATED,
    CONF_CONTAINERS,
    HOST_MON_COND,
    CREATE_SENSORS,
    CONTAINER_MON_COND
)

from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS,
    CONF_NAME
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Docker Sensor."""
    sensors = [DockerHostSensor(
        hass = hass, 
        api = hass.data[DOCKER_CLIENT][DATA_HOST], 
        clientname = config_entry.data[CONF_NAME], 
        variable = variable
    ) for variable in HOST_MON_COND]

    conditions = config_entry.data.get(CONF_MONITORED_CONDITIONS, CONTAINER_MON_COND)
    if type(conditions) is str:
        conditions = conditions.split(',') 

    if config_entry.data[CREATE_SENSORS]:
        for container in hass.data[DOCKER_CLIENT][CONF_CONTAINERS]:
            sensors += [DockerContainerSensor(
                hass = hass, 
                api = hass.data[DOCKER_CLIENT][DATA_HOST], 
                clientname = config_entry.data[CONF_NAME], 
                container_name = container, 
                variable = variable.strip()
            ) for variable in conditions if variable.strip() in CONTAINER_MON_COND]

    if sensors:
        async_add_entities(sensors, True)
    else:
        _LOGGER.info("No containers setup")
        return False

class DockerHostSensor(Entity):
    """Representation of a Docker Sensor."""

    def __init__(self, hass, api, clientname, variable):
        """Initialize the sensor."""
        self._hass = hass
        self._api = api
        self._clientname = clientname
        self._info = None
        self._state = None
        self._attributes = {}
        self._var_id = variable
        self._var_name = HOST_MON_COND[variable][0]
        self._var_unit = HOST_MON_COND[variable][1]
        self._var_icon = HOST_MON_COND[variable][2]
        self._var_class = HOST_MON_COND[variable][3]
        self._var_attr = HOST_MON_COND[variable][4]

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return "docker_{}_{}".format(self._clientname, self._var_name)

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} {}".format(self._clientname, self._var_name)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return self._var_icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._var_class

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._var_unit

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        self.unsub_update = async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    async def async_update(self) -> None:
        self._info = self.hass.data[DOCKER_CLIENT][DATA_VERSION_INFO]
        self._state = self._info.get(self._var_attr, None)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this Docker host instance."""
        return {
            "identifiers": {
                (DOMAIN, self._clientname)
            },
            "name": self._clientname,
            "manufacturer": "Docker",
            "model": "Host",
            "sw_version": self.hass.data[DOCKER_CLIENT][DATA_VERSION_INFO]["version"]
        }

class DockerContainerSensor(Entity):
    """Representation of a Docker Sensor."""

    def __init__(self, hass, api, clientname, container_name, variable):
        """Initialize the sensor."""
        self._hass = hass
        self._api = api
        self._info = None
        self._clientname = clientname
        self._container_name = container_name

        self._var_id = variable
        self._var_name = CONTAINER_MON_COND[variable][0]
        self._var_unit = CONTAINER_MON_COND[variable][1]
        self._var_icon = CONTAINER_MON_COND[variable][2]
        self._var_class = CONTAINER_MON_COND[variable][3]
        self._attributes = {}

        self._state = None
        self._container = api.get_container(container_name)

        _LOGGER.info("Initializing Docker sensor \"{}\" with parameter: {}".format(
            self._container_name, self._var_name))

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return "{}_{}_{}".format(self._clientname, self._container_name, self._var_name)

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return "{} {}".format(self._container_name.title(), self._var_name)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._var_icon

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._var_class

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._var_unit

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        self.unsub_update = async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    async def async_update(self) -> None:
        self._state = self._container.get_info().get(self._var_id, None)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this Docker host instance."""
        return {
            "identifiers": {
                (DOMAIN, self._clientname, self._container_name)
            },
            "name": self._container_name.title(),
            "manufacturer": "Docker",
            "model": "Container",
            "sw_version": self.hass.data[DOCKER_CLIENT][DATA_VERSION_INFO]["version"]
        }