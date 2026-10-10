# The Mach-E cell block

## Layout

The battery energy control module (BECM) answers UDS `22 FD F4` on request ID `0x7E4` / response ID `0x7EC`
with 1131 bytes: `62 FD F4` followed by 1128 data bytes, carried in 162 ISO-TP frames.

The data is 282 big-endian IEEE 754 single-precision floats in three blocks of 94, one value per cell:

| Floats | Content |
|---|---|
| 0–93 | Live cell voltages in volts, cell 1 first |
| 94–187 | Per-cell values around 3.90 V that stay constant between readings |
| 188–281 | Per-cell values around 3.84 V that stay constant between readings |

The program reads the first block and takes the cell count as one third of the data length divided by four.
The BECM refreshes the block every few seconds; consecutive requests within that time return the same
values.

The BECM also broadcasts the cell voltages on CAN frames `0x490`–`0x4A3`, but the gateway does not pass
them to the OBD port.

## Method

The BECM's identifiers `0x0000`–`0x2D8D` and `0x4000`–`0xFFFF` were read in the default diagnostic session.
`0xFDF4` is the only reply that decodes to 94 cell voltages whose sum equals the pack voltage.

## Verification

On a 2021 extended-range car (94 cells):

| Check | Result |
|---|---|
| 94 × mean of block 0 against pack voltage (`0x480D`) | Within 0.5 V |
| Block 0 minimum and mean against the BECM's lowest and average cell voltage (`0x4840`, `0x4841`) | Within a few mV |
| Block 0 between readings | Changes with load |

The battery values and the odometer use the decodings published by OBDb (`Ford-Mustang-Mach-E`),
sillygoose/mme-record and dalathegreat/Battery-Emulator.

## Reading it reliably

A 162-frame reply exposes weak spots in ELM327-style adapters and their links:

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
