# Mach-E Battery Cell Voltage Reader

Reads every cell voltage of a Ford Mustang Mach-E high-voltage battery, together with state of health and
other battery values, through an ELM327-compatible OBD adapter. Shows them in a browser or prints them on
the command line.

![Overview](docs/images/overview.png)

![Cell voltages](docs/images/cell-voltages.png)

![Cell group health](docs/images/group-health.png)

## How it works

The battery energy control module (request `0x7E4`, response `0x7EC`) answers UDS `0x22`
ReadDataByIdentifier requests. Each cell value is one big-endian IEEE 754 float per series cell group:

| Identifier | Content |
|---|---|
| `0xFDE3` | Live cell group voltages: a 16-byte header whose first word is the module's timestamp in 0.1 s, then one float per group. Layout: [docs/cell-block.md](docs/cell-block.md) |
| `0xFDDC` | Eight battery temperature sensors, °C |
| `0xFDCD` | Capacity of each cell group, Ah |
| `0xFDEB` | Balancing active, one byte per cell group |
| `0xFDD3` | Time each cell group has been balancing, 32-bit count of 0.2 s |

`0xFDF4` also holds cell group voltages, but it is a stored snapshot that does not update while the pack
charges; it is not used.

The program only sends UDS `0x22` ReadDataByIdentifier requests.

## Values shown

- **Cell voltages:** every cell group, live, with how long ago the battery module measured them, minimum,
  maximum, mean, spread, standard deviation, outliers, which groups are being balanced and for how long, a
  deviation chart and a table.
- **Cell group health:** capacity of each group and its state of health against the pack capacity at
  100 % (pack capacity divided by pack state of health), weakest and strongest group.
- **Battery:** state of health, capacity, state of charge (BMS and displayed), energy remaining, pack
  voltage, lowest and average cell voltage, battery age.
- **Temperatures:** pack, highest, lowest and average sensor, coolant inlet, and the eight battery
  temperature sensors.
- **Odometer.**

Verified on a 2021 Mach-E extended range (94 cell groups in series) with an OBDLink STN2231 adapter.

## Disclaimer

Ford does not publish these identifiers. The cell-level values were decoded by reverse engineering on one
vehicle:

- every identifier the battery energy control module answers was read and decoded as integers and floats;
- candidate values were compared with the module's own published pack values: the live cell group voltages
  (`0xFDE3`) sum to the pack voltage and match its lowest and average cell voltage, at rest and while
  charging, and the mean group capacity matches the pack capacity;
- the sensor temperatures (`0xFDDC`) were compared with the module's own highest and lowest sensor
  temperature (`0x4808`) on every read;
- readings were repeated at rest and while charging to separate live values from stored ones: the live cell
  voltages changed on every read, while the stored snapshot (`0xFDF4`) stayed frozen for over ten minutes of
  charging; the balancing flags and timers agree group for group, with timers advancing at five counts per
  second.

The module refreshes the live cell group voltages about every 1.2 s. The GUI shows how long ago the module's
timestamp last advanced. The meaning of each value is an interpretation of this data, not a documented
definition. Values may be wrong or differ on other vehicles, battery versions and software levels. Use them for information only,
not for repair or safety decisions. The project is not affiliated with or endorsed by Ford Motor Company.

This software is provided as is, without warranty of any kind, express or implied. You use it entirely at your
own risk; the authors accept no liability for any damage to vehicles, equipment or data, or for any other loss
arising from its use.

## Windows

1. Download `MacheCellVoltageReader-<version>-setup.exe` from the latest
   [GitHub release](../../releases/latest) and run it. No Python or other software is needed.
2. Plug the OBD adapter into the car's OBD port and switch the car on. Connect the adapter to the computer
   with USB, or pair a Bluetooth adapter in Windows first.
3. Start **Mach-E Cell Voltage Reader** from the Start menu. A console window opens and your browser shows
   the reader at `http://127.0.0.1:8080/`. Only this computer can reach it.
4. Select the adapter's COM port and press **Connect**. The port is listed in Windows Device Manager under
   *Ports (COM & LPT)*.
5. To stop the reader, close the console window. Starting it again while it runs only opens the browser.

Each release also contains `MacheCellVoltageReader-<version>-setup.exe.sha256`. To verify the download, run in
PowerShell in the download folder and compare the result with the file's content:

```powershell
(Get-FileHash .\MacheCellVoltageReader-<version>-setup.exe -Algorithm SHA256).Hash
```

The installer's options page offers two choices, both off by default:

- **Start the reader when I log on to Windows** puts a shortcut in your Startup folder. The console window
  and the browser then open at every logon.
- **Allow other devices on my network to open the reader** makes the reader listen on all network
  interfaces. It has no login and no encryption: choose it only on a trusted home network.

With network access, the console window lists the addresses for other devices, for example
`http://192.168.1.20:8080/` or `http://<PC name>:8080/`. Open one of them in the browser of a phone or another
computer on the same network. The computer's own name and addresses are accepted automatically.

Windows Firewall must let those connections through:

- **Installed for all users** (administrator rights): the installer adds an inbound rule for the reader that
  allows only the local subnet on Private networks. Windows shows no prompt.
- **Installed for you only**: Windows asks on the first start whether to allow the reader through the firewall.
  Allow **Private networks** only and clear **Public networks**. If you chose Cancel, allow
  `MacheCells.exe` under *Windows Security > Firewall & network protection > Allow an app through firewall*.

The network must be classified as Private in *Settings > Network & internet*.

To change these options, run the installer again and change the choices on the options page, or uninstall under
*Settings > Apps*, which also removes the Startup shortcut and the firewall rule. The other settings in the
Configuration section work as Windows environment variables, for example `MACHE_PORT` for another port. An
explicitly set `MACHE_HOST` takes precedence over the installer's network option.

Build the installer on a Windows machine with Python 3.14, Node.js 24 and Inno Setup 6.7.1:

```powershell
./packaging/build.ps1
```

The result is `packaging/build/installer/MacheCellVoltageReader-<version>-setup.exe`. The version is read
from `pyproject.toml`. Pushing a tag `v*` builds the installer in GitHub Actions and attaches it to a release.

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
| `MACHE_PORT_PATTERNS` | `/dev/ttyUSB*,/dev/ttyACM*,/dev/rfcomm*` (Windows: `COM*`) | Device globs offered as ports |
| `MACHE_HOST` | `127.0.0.1` (Docker image: `0.0.0.0`, published on `MACHE_BIND_ADDRESS`) | Address the GUI listens on |
| `MACHE_PORT` | `8080` | Port the GUI listens on |
| `MACHE_ALLOWED_HOSTS` | empty | Comma-separated host names or IP addresses, besides `localhost`, `127.0.0.1` and `[::1]`, that the GUI answers to |

On a Bluetooth or USB-over-network link, use `MACHE_SEPARATION_MS=20` and `MACHE_FRAME_TIMEOUT_MS=60`.

## Network access

By default only the computer running the reader can reach it. The reader has no login and no encryption: anyone
who can reach it sees the battery data and can connect or disconnect the adapter. Enable network access only on
a trusted home network, and never port-forward it or expose it to the internet.

- **Windows application:** select *Allow other devices on my network to open the reader* in the installer
  (see [Windows](#windows)), then restart the reader. Open one of the addresses printed in the console window,
  such as `http://<PC name or IP address>:8080/`, on the other device. Without the installer, set the user
  environment variable `MACHE_HOST=0.0.0.0`.
- **Docker:** set `MACHE_BIND_ADDRESS=0.0.0.0` and `MACHE_ALLOWED_HOSTS=<host name or IP address as typed in the
  browser>` in `.env`, then run `docker compose up -d app`.

A request whose `Host` header is not `localhost`, `127.0.0.1`, `[::1]` or listed in `MACHE_ALLOWED_HOSTS` is
refused. When the reader listens on all interfaces (`MACHE_HOST=0.0.0.0`), the computer's own host name and
IP addresses are accepted as well; use `MACHE_ALLOWED_HOSTS` for any other name, such as one set in your router.
The live data stream refuses connections from a page on another origin.

## Development

The GUI is a Vue 3 + Vite + TypeScript app in `frontend/`. It receives every reading and connection change
over the WebSocket `/api/events` and reconnects automatically. Node and npm run only in Docker.

```sh
docker compose run --rm --build checks            # ruff, mypy --strict, pytest
docker compose run --rm --build frontend-checks   # eslint, stylelint, vue-tsc, vitest, vite build
docker compose run --rm --build screenshot        # README images from a running, connected GUI
```

Build an installable wheel that includes the built GUI (written to `dist/`):

```sh
docker compose run --rm --build wheel
```

`pip wheel` outside this service produces a wheel without the GUI, because the frontend is built in the
Docker image.
