import pytest

from mache_cells.elm327 import AdapterError, CorruptReply, Elm327, NoResponse
from mache_cells.transport import ReplyLost
from mache_cells.uds import NegativeResponse, UdsClient
from tests.conftest import FakeAdapter


class ScriptedTransport:
    def __init__(self, replies: dict[str, list[str]]) -> None:
        self.replies = replies
        self.sent: list[str] = []

    def exchange(self, command: str, timeout_s: float) -> list[str]:
        self.sent.append(command)
        reply = self.replies.get(command, ["OK"])
        if reply == ["LOST"]:
            raise ReplyLost("reply lost")
        return reply

    def close(self) -> None:
        self.sent.append("closed")


def adapter(transport: ScriptedTransport) -> Elm327:
    return Elm327(
        transport, command_timeout_s=1.0, reset_timeout_s=1.0, separation_ms=20, frame_timeout_ms=60
    )


def test_initialize_replaces_adaptive_timing() -> None:
    transport = ScriptedTransport({"ATZ": ["ELM327 v1.4b"], "ATI": ["ELM327 v1.4b"]})

    adapter(transport).initialize()

    assert transport.sent[transport.sent.index("ATAL") + 1 :][:2] == ["ATAT0", "ATST0F"]


def test_flow_control_asks_for_the_separation_time() -> None:
    transport = ScriptedTransport({"22480D": ["NO DATA"]})

    with pytest.raises(NoResponse):
        adapter(transport).request(0x7E4, 0x7EC, bytes.fromhex("22480D"))

    assert "ATFCSD300014" in transport.sent


@pytest.mark.parametrize(("separation", "frame_timeout"), [(200, 300), (20, 20), (5, 2000)])
def test_invalid_timing_is_rejected(separation: int, frame_timeout: int) -> None:
    with pytest.raises(ValueError):
        Elm327(ScriptedTransport({}), 1.0, 1.0, separation_ms=separation, frame_timeout_ms=frame_timeout)


def test_bus_fault_is_not_mistaken_for_silence() -> None:
    with pytest.raises(AdapterError, match="CAN ERROR") as fault:
        adapter(ScriptedTransport({"22480D": ["CAN ERROR"]})).request(0x7E4, 0x7EC, bytes.fromhex("22480D"))

    assert not isinstance(fault.value, NoResponse)


def test_truncated_frames_are_corrupt_reply() -> None:
    frames = ["7EC100A62FDF455AA00", "7EC2100000000000000", "7EC28C00"]

    with pytest.raises(CorruptReply):
        adapter(ScriptedTransport({"22FDF4": frames})).request(0x7E4, 0x7EC, bytes.fromhex("22FDF4"))


def test_lost_reply_is_corrupt_reply_and_readdresses() -> None:
    transport = ScriptedTransport({"22FDF4": ["LOST"]})
    elm = adapter(transport)

    with pytest.raises(CorruptReply, match="reply lost"):
        elm.request(0x7E4, 0x7EC, bytes.fromhex("22FDF4"))
    transport.replies["22FDF4"] = ["7EC0562FDF40102"]
    elm.request(0x7E4, 0x7EC, bytes.fromhex("22FDF4"))

    assert transport.sent.count("ATSH7E4") == 2


def test_unsupported_identifier_is_negative_response(fake_adapter: FakeAdapter) -> None:
    elm = Elm327(fake_adapter, 1.0, 1.0, separation_ms=5, frame_timeout_ms=200)

    with pytest.raises(NegativeResponse, match="requestOutOfRange"):
        UdsClient(elm).read_did(0x7E4, 0x7EC, 0x1234)


def test_response_pending_is_skipped() -> None:
    transport = ScriptedTransport({"22480D": ["7EC037F2278", "7EC0562480D8B88"]})

    assert UdsClient(adapter(transport)).read_did(0x7E4, 0x7EC, 0x480D) == bytes.fromhex("8B88")
