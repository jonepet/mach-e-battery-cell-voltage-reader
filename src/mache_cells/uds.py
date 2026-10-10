from typing import Protocol

NRC_NAMES = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLengthOrInvalidFormat",
    0x22: "conditionsNotCorrect",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x78: "requestCorrectlyReceivedResponsePending",
    0x7F: "serviceNotSupportedInActiveSession",
}


class UdsError(Exception):
    pass


class NegativeResponse(UdsError):
    def __init__(self, service: int, code: int) -> None:
        super().__init__(f"service {service:02X} rejected: {NRC_NAMES.get(code, 'NRC')} ({code:02X})")
        self.service = service
        self.code = code


class RequestChannel(Protocol):
    def request(self, tx_id: int, rx_id: int, payload: bytes) -> list[bytes]: ...


class UdsClient:
    """ISO 14229 client whose only request is 0x22 ReadDataByIdentifier, so it cannot change any module."""

    def __init__(self, channel: RequestChannel) -> None:
        self._channel = channel

    def read_did(self, tx_id: int, rx_id: int, did: int) -> bytes:
        did_bytes = did.to_bytes(2, "big")
        messages = self._channel.request(tx_id, rx_id, b"\x22" + did_bytes)
        final = [m for m in messages if m and not (m[0] == 0x7F and m[2:3] == b"\x78")]
        if not final:
            raise UdsError(f"DID {did:04X} from {rx_id:03X}: no final response")
        response = final[-1]
        if response[0] == 0x7F and len(response) >= 3:
            raise NegativeResponse(response[1], response[2])
        if response[:3] != b"\x62" + did_bytes:
            raise UdsError(
                f"DID {did:04X} from {rx_id:03X}: unexpected response {response[:3].hex().upper()}"
            )
        return response[3:]
