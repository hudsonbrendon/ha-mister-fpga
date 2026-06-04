from unittest.mock import AsyncMock, patch

from homeassistant.data_entry_flow import FlowResultType
from mister_fpga.ra_web import MisterRAWebError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mister_fpga.const import (
    CONF_RA_API_KEY,
    CONF_RA_USERNAME,
    DOMAIN,
)


async def _options_flow(hass, user_input):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"}, options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )


async def test_options_invalid_ra_creds_show_error(hass):
    with patch(
        "custom_components.mister_fpga.config_flow.MisterRAWeb"
    ) as mock_web:
        mock_web.return_value.async_validate = AsyncMock(
            side_effect=MisterRAWebError("bad")
        )
        mock_web.return_value.async_close = AsyncMock()
        result = await _options_flow(
            hass, {CONF_RA_USERNAME: "u", CONF_RA_API_KEY: "bad"}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_options_valid_ra_creds_create_entry(hass):
    with patch(
        "custom_components.mister_fpga.config_flow.MisterRAWeb"
    ) as mock_web:
        mock_web.return_value.async_validate = AsyncMock(return_value=None)
        mock_web.return_value.async_close = AsyncMock()
        result = await _options_flow(
            hass, {CONF_RA_USERNAME: "u", CONF_RA_API_KEY: "good"}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_options_no_ra_creds_skip_validation(hass):
    result = await _options_flow(hass, {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
