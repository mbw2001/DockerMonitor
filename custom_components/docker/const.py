"""Constants for the Docker integration."""
DOMAIN = 'docker'

DEFAULT_NAME = 'DockerHost'
DEFAULT_HOST = 'unix://var/run/docker.sock'
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_CREATE_SENSORS = True

CREATE_SENSORS = 'create_sensors'

DOCKER_CLIENT = 'docker_client'
DATA_UPDATED = "docker_data_updated"
DATA_VERSION_INFO = 'docker_version_info'
DATA_HOST = 'docker_host'
CONF_CONTAINERS = 'docker_containers'

COMPONENTS = ['sensor', 'switch']

PRECISION = 2

HOST_MON_COND = {
    'host_version': ['Version', None, 'mdi:information-outline', None, 'version'],
    'host_apiversion': ['ApiVersion', None, 'mdi:information-outline', None, 'api_version'],
    'host_os': ['OS', None, 'mdi:information-outline', None, 'os'],
    'host_archiecture': ['Architecture', None, 'mdi:information-outline', None, 'arch'],
}

CONTAINER_MON_COND = {
    'container_status': ['Status', None, 'mdi:checkbox-marked-circle-outline', None],
    'container_uptime': ['Up Time', '', 'mdi:clock', 'timestamp'],
    'container_image': ['Image', None, 'mdi:information-outline', None]
}