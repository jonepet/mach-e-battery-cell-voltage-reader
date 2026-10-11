import pytest

from mache_cells.config import Settings


def test_linux_defaults_offer_serial_devices() -> None:
    settings = Settings.from_env({}, platform="linux")

    assert settings.port_patterns == ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/rfcomm*")


def test_windows_defaults_offer_com_ports() -> None:
    settings = Settings.from_env({}, platform="win32")

    assert "COM*" in settings.port_patterns


@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_environment_overrides_the_platform_default(platform: str) -> None:
    settings = Settings.from_env({"MACHE_PORT_PATTERNS": "/dev/ttyS*,COM1"}, platform=platform)

    assert settings.port_patterns == ("/dev/ttyS*", "COM1")
