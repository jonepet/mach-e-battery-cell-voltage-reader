import pytest

from mache_cells.config import Settings


def test_linux_defaults_offer_serial_devices() -> None:
    settings = Settings.from_env({}, platform="linux")

    assert settings.port_patterns == ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/rfcomm*")


def test_gui_listens_on_loopback_and_allows_no_extra_hosts_by_default() -> None:
    settings = Settings.from_env({})

    assert (settings.host, settings.allowed_hosts) == ("127.0.0.1", ())


def test_allowed_hosts_are_a_trimmed_comma_separated_list() -> None:
    settings = Settings.from_env({"MACHE_ALLOWED_HOSTS": " pc.home,192.168.1.20 ,,"})

    assert settings.allowed_hosts == ("pc.home", "192.168.1.20")


def test_windows_defaults_offer_com_ports() -> None:
    settings = Settings.from_env({}, platform="win32")

    assert "COM*" in settings.port_patterns


@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_environment_overrides_the_platform_default(platform: str) -> None:
    settings = Settings.from_env({"MACHE_PORT_PATTERNS": "/dev/ttyS*,COM1"}, platform=platform)

    assert settings.port_patterns == ("/dev/ttyS*", "COM1")
