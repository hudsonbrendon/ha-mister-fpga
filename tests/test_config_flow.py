"""Tests for the MiSTer FPGA config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from mister_fpga import MisterConnectionError, MisterStatus

from custom_components.mister_fpga.const import DOMAIN


async def test_user_flow_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM

    with patch(
        "mister_fpga.client.MisterClient.async_get_status",
        new=AsyncMock(return_value=MisterStatus(online=True)),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "MiSTer FPGA", CONF_HOST: "192.168.31.77", CONF_PORT: 8182},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MiSTer FPGA"
    assert result["data"][CONF_HOST] == "192.168.31.77"


async def test_user_flow_cannot_connect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with patch(
        "mister_fpga.client.MisterClient.async_get_status",
        new=AsyncMock(side_effect=MisterConnectionError("boom")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "MiSTer FPGA", CONF_HOST: "192.168.31.77", CONF_PORT: 8182},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
