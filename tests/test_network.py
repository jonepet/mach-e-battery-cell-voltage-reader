import socket
from typing import Any

import pytest

from mache_cells import network


def fake_addrinfo(*addresses: str) -> Any:
    def getaddrinfo(host: str, port: object) -> list[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 0)) for address in addresses]

    return getaddrinfo


@pytest.mark.parametrize("host", ["", "0.0.0.0", "::"])
def test_wildcard_addresses_listen_on_all_interfaces(host: str) -> None:
    assert network.listens_on_all_interfaces(host)


@pytest.mark.parametrize("host", ["127.0.0.1", "192.168.1.20", "::1"])
def test_specific_addresses_do_not_listen_on_all_interfaces(host: str) -> None:
    assert not network.listens_on_all_interfaces(host)


def test_local_names_are_the_lowercase_host_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "gethostname", lambda: "DESKTOP-ABC")

    assert network.local_names() == ("desktop-abc",)


def test_usable_addresses_are_listed_once_in_host_header_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        fake_addrinfo("127.0.0.1", "192.168.1.20", "fe80::1%12", "fd00::20", "169.254.3.4", "192.168.1.20"),
    )
    monkeypatch.setattr(network, "_routed_address", lambda family, target: None)

    assert network.local_addresses() == ("192.168.1.20", "[fd00::20]")


def test_routed_interface_address_is_included(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", fake_addrinfo("127.0.1.1"))
    monkeypatch.setattr(
        network, "_routed_address", lambda family, target: "10.0.0.7" if family == socket.AF_INET else None
    )

    assert network.local_addresses() == ("10.0.0.7",)


def test_unresolvable_host_name_leaves_the_routed_address(monkeypatch: pytest.MonkeyPatch) -> None:
    def unresolvable(host: str, port: object) -> list[tuple[Any, ...]]:
        raise socket.gaierror

    monkeypatch.setattr(socket, "getaddrinfo", unresolvable)
    monkeypatch.setattr(network, "_routed_address", lambda family, target: "10.0.0.7")

    assert network.local_addresses() == ("10.0.0.7",)
