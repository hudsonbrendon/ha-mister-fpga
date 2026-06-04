from custom_components.mister_fpga import const


def test_ra_cloud_constants():
    assert const.CONF_RA_API_KEY == "ra_api_key"
    assert const.CONF_RA_USERNAME == "ra_username"
    assert const.CONF_RA_CLOUD_INTERVAL == "ra_cloud_interval"
    assert const.DEFAULT_RA_CLOUD_INTERVAL == 300
    assert const.MIN_RA_CLOUD_INTERVAL == 60
    assert const.MAX_RA_CLOUD_INTERVAL == 3600
