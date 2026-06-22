from mcp_bridge.config.initial import InitialSettings


def test_default_config_file_points_to_package_config() -> None:
    assert InitialSettings(_env_file=None).file == "mcp_bridge/config.json"
