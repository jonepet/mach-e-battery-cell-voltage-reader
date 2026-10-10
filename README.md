# Mach-E Battery Cell Voltage Reader

Reads every cell voltage of a Ford Mustang Mach-E high-voltage battery, together with state of health and
other battery values, through an ELM327-compatible OBD adapter. Shows them in a browser or prints them on
the command line.

![Overview](docs/images/overview.png)

![Cell voltages](docs/images/cell-voltages.png)

## How it works

The battery energy control module (request `0x7E4`, response `0x7EC`) returns all cell voltages as
big-endian IEEE 754 floats in its reply to UDS `22 FD F4`. Layout and verification:
[docs/cell-block.md](docs/cell-block.md).

The program only sends UDS `0x22` ReadDataByIdentifier requests.

## Values shown

- **Cell voltages:** every cell, with minimum, maximum, mean, spread, standard deviation, outliers, a
  deviation chart and a table.
- **Battery:** state of health, capacity, state of charge (BMS and displayed), energy remaining, pack
  voltage, lowest and average cell voltage, battery age.
- **Temperatures:** pack, highest, lowest and average sensor, coolant inlet.
- **Odometer.**

Verified on a 2021 Mach-E extended range (94 cells) with an OBDLink STN2231 adapter.

## Run

Requires Docker with Compose and an ELM327-compatible adapter (CAN 11-bit, 500 kbit/s) on the OBD port,
with the car switched on.

```sh
cp .env.example .env
docker compose up -d --build app
```

Open `http://localhost:8080`, select the adapter port and press **Connect**.

Single reading on the command line:

```sh
docker compose run --rm app mache-cells read /dev/ttyUSB0
docker compose run --rm app mache-cells read /dev/ttyUSB0 --json
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MACHE_BIND_ADDRESS` | `127.0.0.1` | Host address the GUI is published on |
| `MACHE_PUBLISH_PORT` | `8080` | Host port of the GUI |
| `MACHE_READ_INTERVAL_S` | `2.0` | Minimum seconds between readings |
| `MACHE_BAUDRATE` | `115200` | Serial speed to the adapter |
| `MACHE_COMMAND_TIMEOUT_S` | `2.0` | Silence after which the adapter is considered unresponsive |
| `MACHE_RESET_TIMEOUT_S` | `5.0` | Adapter reset timeout |
| `MACHE_SEPARATION_MS` | `5` | Separation time (0–127 ms) between frames of the cell reply |
| `MACHE_FRAME_TIMEOUT_MS` | `200` | Adapter wait per frame, above the separation time (at most 1020) |
| `MACHE_OUTLIER_DEVIATION_V` | `0.02` | Deviation from the median that flags a cell |
| `MACHE_SPREAD_WARNING_V` | `0.05` | Spread that is flagged |
| `MACHE_PORT_PATTERNS` | `/dev/ttyUSB*,/dev/ttyACM*,/dev/rfcomm*` | Device globs offered as ports |

On a Bluetooth or USB-over-network link, use `MACHE_SEPARATION_MS=20` and `MACHE_FRAME_TIMEOUT_MS=60`.

## Development

```sh
docker compose run --rm --build checks       # ruff, mypy --strict, pytest
docker compose run --rm --build screenshot   # README images from a running, connected GUI
```
