import pytest

from mache_cells.isotp import IsoTpError, parse_frame, reassemble
from tests.conftest import segment


def test_multi_frame_reply_is_reassembled() -> None:
    payload = bytes(range(40))
    frames = [parse_frame(f"7EC{frame.hex()}") for frame in segment(payload)]

    assert reassemble(frames, 0x7EC) == [payload]


def test_frames_from_other_ids_are_ignored() -> None:
    frames = [parse_frame("7E803410C00"), parse_frame("7EC0562480D8B88")]

    assert reassemble(frames, 0x7EC) == [bytes.fromhex("62480D8B88")]


def test_lost_consecutive_frame_is_detected() -> None:
    frames = [parse_frame(f"7EC{frame.hex()}") for frame in segment(bytes(40))]
    del frames[2]

    with pytest.raises(IsoTpError, match="frame sequence"):
        reassemble(frames, 0x7EC)


def test_truncated_line_is_not_a_frame() -> None:
    with pytest.raises(IsoTpError, match="not an 11-bit CAN frame"):
        parse_frame("7EC28C00")
