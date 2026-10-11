"""Names and addresses under which other devices on the local network reach this computer."""

import ipaddress
import socket

WILDCARD_ADDRESSES = ("", "0.0.0.0", "::")
# Documentation ranges (RFC 5737, RFC 3849): connecting a UDP socket to them sends nothing and only selects
# the interface the operating system would route through.
ROUTE_PROBES = ((socket.AF_INET, "192.0.2.1"), (socket.AF_INET6, "2001:db8::1"))
DISCARD_PORT = 9


def listens_on_all_interfaces(host: str) -> bool:
    return host in WILDCARD_ADDRESSES


def _routed_address(family: socket.AddressFamily, target: str) -> str | None:
    try:
        with socket.socket(family, socket.SOCK_DGRAM) as probe:
            probe.connect((target, DISCARD_PORT))
            return str(probe.getsockname()[0])
    except OSError:
        return None


def _resolved_addresses(host_name: str) -> list[str]:
    try:
        return [str(info[4][0]) for info in socket.getaddrinfo(host_name, None)]
    except socket.gaierror:
        return []


def _host_header_form(text: str) -> str | None:
    """The address as a browser writes it in a Host header, or None when other devices cannot use it."""
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return None
    if address.is_loopback or address.is_unspecified or address.is_link_local:
        return None
    return f"[{address}]" if address.version == 6 else str(address)


def local_names() -> tuple[str, ...]:
    return (socket.gethostname().lower(),)


def local_addresses() -> tuple[str, ...]:
    routed = (_routed_address(family, target) for family, target in ROUTE_PROBES)
    candidates = (*_resolved_addresses(socket.gethostname()), *(address for address in routed if address))
    return tuple(dict.fromkeys(form for form in map(_host_header_form, candidates) if form))


def local_hosts() -> tuple[str, ...]:
    return (*local_names(), *local_addresses())
