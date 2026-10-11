import sys
from collections.abc import Mapping
from dataclasses import dataclass

from mache_cells.elm327 import check_timing

POSIX_PORT_PATTERNS = ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/rfcomm*")
WINDOWS_PORT_PATTERNS = ("COM*",)


def default_port_patterns(platform: str) -> tuple[str, ...]:
    return WINDOWS_PORT_PATTERNS if platform == "win32" else POSIX_PORT_PATTERNS


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    baudrate: int
    read_interval_s: float
    command_timeout_s: float
    reset_timeout_s: float
    separation_ms: int
    frame_timeout_ms: int
    outlier_deviation_v: float
    spread_warning_v: float
    port_patterns: tuple[str, ...]

    @classmethod
    def from_env(cls, env: Mapping[str, str], platform: str = sys.platform) -> "Settings":
        settings = cls(
            host=env.get("MACHE_HOST", "0.0.0.0"),
            port=int(env.get("MACHE_PORT", "8080")),
            baudrate=int(env.get("MACHE_BAUDRATE", "115200")),
            read_interval_s=float(env.get("MACHE_READ_INTERVAL_S", "2.0")),
            command_timeout_s=float(env.get("MACHE_COMMAND_TIMEOUT_S", "2.0")),
            reset_timeout_s=float(env.get("MACHE_RESET_TIMEOUT_S", "5.0")),
            separation_ms=int(env.get("MACHE_SEPARATION_MS", "5")),
            frame_timeout_ms=int(env.get("MACHE_FRAME_TIMEOUT_MS", "200")),
            outlier_deviation_v=float(env.get("MACHE_OUTLIER_DEVIATION_V", "0.02")),
            spread_warning_v=float(env.get("MACHE_SPREAD_WARNING_V", "0.05")),
            port_patterns=(
                tuple(env["MACHE_PORT_PATTERNS"].split(","))
                if "MACHE_PORT_PATTERNS" in env
                else default_port_patterns(platform)
            ),
        )
        check_timing(settings.separation_ms, settings.frame_timeout_ms)
        return settings
