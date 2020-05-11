"""Config flow to configure the Docker integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    CONF_MONITORED_CONDITIONS
)
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_CREATE_SENSORS,
    CREATE_SENSORS,
    HOST_MON_COND,
    CONTAINER_MON_COND,
    CONF_CONTAINERS
)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
    vol.Optional(CONF_MONITORED_CONDITIONS): str,
    vol.Required(CREATE_SENSORS, default=DEFAULT_CREATE_SENSORS): bool
})

class DockerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Docker config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title = user_input[CONF_NAME],
                data = user_input
            )

        return self.async_show_form(
            step_id="user", 
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DockerOptionsFlowHandler(config_entry)

class DockerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Docker client options."""

    def __init__(self, config_entry):
        """Initialize Docker options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the Docker options."""
        if user_input is not None:
            return self.async_create_entry(title = "", data = user_input)

        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )): int
        }))