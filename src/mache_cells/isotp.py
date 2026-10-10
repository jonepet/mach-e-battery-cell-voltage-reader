from dataclasses import dataclass


class IsoTpError(Exception):
    pass


@dataclass(frozen=True)
class CanFrame:
    can_id: int
    data: bytes


def parse_frame(line: str) -> CanFrame:
    """Parse one ELM327 output line produced with ATH1 ATS0 on an 11-bit bus: 3 hex id chars then data."""
    compact = line.replace(" ", "")
    if len(compact) < 5 or len(compact) % 2 == 0:
        raise IsoTpError(f"not an 11-bit CAN frame: {line!r}")
    try:
        return CanFrame(can_id=int(compact[:3], 16), data=bytes.fromhex(compact[3:]))
    except ValueError as exc:
        raise IsoTpError(f"not an 11-bit CAN frame: {line!r}") from exc


def reassemble(frames: list[CanFrame], rx_id: int) -> list[bytes]:
    """Reassemble every ISO 15765-2 message addressed from rx_id, in arrival order."""
    messages: list[bytes] = []
    pending: bytearray | None = None
    expected_length = 0
    next_sequence = 0
    for frame in (f for f in frames if f.can_id == rx_id):
        if not frame.data:
            raise IsoTpError(f"empty frame from {rx_id:03X}")
        pci_type = frame.data[0] >> 4
        if pci_type == 0x0:
            length = frame.data[0] & 0x0F
            if not 0 < length < len(frame.data):
                raise IsoTpError(
                    f"single frame from {rx_id:03X} declares {length} bytes in {frame.data.hex()}"
                )
            messages.append(frame.data[1 : 1 + length])
            continue
        if pci_type == 0x1:
            if len(frame.data) < 2:
                raise IsoTpError(f"truncated first frame from {rx_id:03X}")
            expected_length = ((frame.data[0] & 0x0F) << 8) | frame.data[1]
            pending = bytearray(frame.data[2:])
            next_sequence = 1
            continue
        if pci_type != 0x2:
            continue
        if pending is None:
            raise IsoTpError(f"consecutive frame from {rx_id:03X} without first frame")
        sequence = frame.data[0] & 0x0F
        if sequence != next_sequence:
            raise IsoTpError(f"frame sequence {sequence} from {rx_id:03X}, expected {next_sequence}")
        pending += frame.data[1:]
        next_sequence = (next_sequence + 1) & 0x0F
        if len(pending) >= expected_length:
            messages.append(bytes(pending[:expected_length]))
            pending = None
    if pending is not None:
        raise IsoTpError(f"incomplete message from {rx_id:03X}: {len(pending)}/{expected_length} bytes")
    return messages
