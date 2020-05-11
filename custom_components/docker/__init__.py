""" Docker custom component """
import logging
import docker
from datetime import timedelta
from dateutil import parser

from typing import Any, Dict

from .const import (
    DOMAIN,
    DOCKER_CLIENT,
    DATA_HOST,
    DATA_VERSION_INFO,
    DATA_UPDATED,
    CONF_CONTAINERS,
    COMPONENTS,
    PRECISION,
    DEFAULT_SCAN_INTERVAL,
    CONTAINER_MON_COND,
    CREATE_SENSORS
)
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_MONITORED_CONDITIONS,
    CONF_SCAN_INTERVAL
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import slugify as util_slugify
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistantType, config_entry: ConfigType) -> bool:
    """Configure Docker using config flow only."""
    if DOMAIN in config_entry:
        for entry in config_entry[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": SOURCE_IMPORT}, data=entry
                )
            )
    return True

async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigType) -> bool:
    """Set up the Docker component."""
    client = DockerHost(hass, config_entry)
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = client
    if not await client.async_setup():
        return False

    return True


async def async_unload_entry(hass: HomeAssistantType, config_entry: ConfigType) -> bool:
    """Unload Docker config entry."""
    hass.config_entries.async_forward_entry_unload(config_entry, 'switch')
    hass.config_entries.async_forward_entry_unload(config_entry, 'sensor')
    hass.data[DOCKER_CLIENT] = {}
    return True

class DockerHost:
    def __init__(self, hass: HomeAssistantType, config_entry: ConfigType):
        self.hass = hass
        self.config_entry = config_entry
        self.api = None
        self.unsub_timer = None
        self.containers = {}

    async def async_setup(self):
        """Set up the Docker client."""
        try:
            self.api = docker.DockerClient(base_url=self.config_entry.data[CONF_HOST])
            _LOGGER.debug("Successfully connected to Docker")
        except Exception as e:
            _LOGGER.error("Can not connect to Docker ({})".format(e))
            raise ConfigEntryNotReady

        self.hass.data[DOCKER_CLIENT] = {}
        self.hass.data[DOCKER_CLIENT][DATA_HOST] = self
        self.hass.data[DOCKER_CLIENT][CONF_CONTAINERS] = []

        self.add_options()
        self.set_scan_interval(self.config_entry.options[CONF_SCAN_INTERVAL])
        self.config_entry.add_update_listener(self.async_options_updated)

        await self.async_update()
        
        for component in COMPONENTS:
            self.hass.async_create_task(
                self.hass.config_entries.async_forward_entry_setup(self.config_entry, component)
            )

        return True

    def add_options(self):
        """Add options for Docker integration."""
        if not self.config_entry.options:
            options = {CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL}
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=options
            )

    def set_scan_interval(self, scan_interval):
        """Update scan interval."""
        if self.unsub_timer is not None:
            self.unsub_timer()
        self.unsub_timer = async_track_time_interval(
            self.hass, self.async_update, timedelta(seconds=scan_interval)
        )
    
    @staticmethod
    async def async_options_updated(hass, entry):
        """Triggered by config entry options updates."""
        hass.data[DOMAIN][entry.entry_id].set_scan_interval(
            entry.options[CONF_SCAN_INTERVAL]
        )

    async def async_update(self, event_time=None) -> None:
        """Get the latest data from the Docker REST API."""
        if self.hass.data[DOCKER_CLIENT] == {}:
            self.unsub_timer = None
            return
        try:
            await self.hass.async_add_executor_job(self.update_host_info)
            await self.hass.async_add_executor_job(self.update_containers)
            async_dispatcher_send(self.hass, DATA_UPDATED)
            _LOGGER.debug("Docker data updated")
        except Exception as e:
            _LOGGER.error("Unable to fetch data from Docker ({})".format(e))

    def update_host_info(self) -> None:
        try:
            raw_stats = self.api.version()
            self.hass.data[DOCKER_CLIENT][DATA_VERSION_INFO] = {
                'version': raw_stats.get('Version', None),
                'api_version': raw_stats.get('ApiVersion', None),
                'os': raw_stats.get('Os', None),
                'arch': raw_stats.get('Arch', None),
                'kernel': raw_stats.get('KernelVersion', None),
            }
        except Exception as e:
            _LOGGER.error("Cannot get Docker version ({})".format(e))

    def update_containers(self) -> None:
        _LOGGER.debug("Updating containers...")
        for container in self.api.containers.list(all=True) or []:
            if container.name not in self.containers:
                _LOGGER.debug("Found container: {}".format(container.name))
                self.containers[container.name] = DockerContainer(self.hass, self.api, container.name)
            self.containers[container.name].update_stats()

        self.hass.data[DOCKER_CLIENT][CONF_CONTAINERS] = list(self.containers.keys())
        async_dispatcher_send(self.hass, DATA_UPDATED)

    def get_container(self, name):
        container = None
        if name in self.containers:
            container = self.containers[name]
        return container

class DockerContainer:
    def __init__(self, hass, hostApi, name):
        self.hostApi = hostApi
        self.name = name
        self.state = False
        self.status = ""
        self.uptime = dt_util.as_local(dt_util.now())
        self.image = ""
        self.cpu = ""
        self.memory = ""
        self.network = ""
        self.container = hostApi.containers.get(name)
         
    def get_name(self):
        return self.name

    def get_state(self):
        return self.state

    def update_stats(self):
        try:
            self.container.reload()
        except Exception as e:
            _LOGGER.error("Cannot get Docker version ({})".format(e))
        self.status = self.container.attrs['State']['Status']
        self.state = self.status == "running"
        up_time = parser.parse(self.container.attrs['State']['StartedAt'])
        if up_time is not None:
            self.uptime = dt_util.as_local(up_time).isoformat()
        self.image = self.container.image.tags[0]

    def get_info(self):
        conditions = list(CONTAINER_MON_COND.keys())
        return {
            conditions[0]: self.status,
            conditions[1]: self.uptime,
            conditions[2]: self.image
        }
        
    def start(self):
        _LOGGER.info("Starting container {}".format(self.name))
        self.state = True
        self.container.start()

    def stop(self, timeout=10):
        _LOGGER.info("Stopping container {}".format(self.name))
        self.state = False
        self.container.stop(timeout=timeout)