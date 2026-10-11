# The Mach-E cell voltage block

## Layout

The battery energy control module (BECM) answers UDS `22 FD E3` on request ID `0x7E4` / response ID `0x7EC`
with `62 FD E3` followed by 392 data bytes on the 94-group extended-range pack:

| Bytes | Content |
|---|---|
| 0–15 | Header. Word 0 (big-endian uint32) is the module's timestamp in 0.1 s ticks; it advances about 12 ticks per refresh |
| 16–391 | One big-endian IEEE 754 single-precision float per series cell group, in volts, group 1 first |

The program takes the group count from the data length after the header. The module refreshes the block
about every 1.2 s; the values change on every refresh, while charging as well as at rest.

`22 FD F4` returns three runs of 94 floats. It is a stored snapshot that did not change for over ten minutes
while the pack charged, and the program does not use it.

The BECM also broadcasts the cell voltages on CAN frames `0x490`–`0x4A3`, but the gateway does not pass
them to the OBD port.

## Verification

On a 2021 extended-range car (94 cell groups), at rest and while charging:

| Check | Result |
|---|---|
| Mean of the groups against the BECM's average cell voltage (`0x4841`) | Within 1 mV |
| Minimum against the BECM's lowest cell voltage (`0x4840`) | Equal |
| Sum of the groups against pack voltage (`0x480D`) | Within 0.2 V |
| Block between reads | Changes; timestamp advances |

`22 FD DC` returns 32 bytes: eight big-endian floats, the battery temperature sensors in °C. Their highest
and lowest values match the BECM's integer sensor maximum and minimum (`0x4808`) on every read.

The battery values and the odometer use the decodings published by OBDb (`Ford-Mustang-Mach-E`),
sillygoose/mme-record and dalathegreat/Battery-Emulator.

## Reading it reliably

A reply of about 57 ISO-TP frames exposes weak spots in ELM327-style adapters and their links:

- **Pacing.** The module is asked for a separation time between frames (`ATFCSD`), so it does not send
  faster than the adapter can pass the frames on.
- **Fixed frame timeout.** Adaptive timing (`ATAT1`, the default) learns from fast single-frame replies and
  ends the long reply between two frames; the remaining frames then arrive as the reply to the next request
  and corrupt it. The program turns adaptive timing off and sets a fixed wait per frame (`ATAT0`, `ATST`).
- **NUL characters.** The adapter emits occasional `0x00` characters, which the ELM327 data sheet says to
  ignore.
- **Lost bytes.** On a lossy link (Bluetooth, USB over a network) bytes can be lost; ISO-TP sequence numbers
  and the length check reveal it, and the reading is reported as damaged instead of decoded. If the final
  prompt is lost, the program resynchronises with the adapter instead of dropping the connection.
