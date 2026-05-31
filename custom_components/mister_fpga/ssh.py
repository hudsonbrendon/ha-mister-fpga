"""Optional SSH telemetry client for the MiSTer FPGA integration."""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

_SEP = "|||"


def parse_ssh_probe(raw: str) -> dict:
    """Parse the batched SSH probe output into a telemetry dict. Tolerant of blanks."""
    parts = [p.strip() for p in raw.split(_SEP)]
    while len(parts) < 5:
        parts.append("")
    core, uptime_s, load_s, mem_s, fw_s = parts[:5]

    def _int(value: str) -> int | None:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    uptime = _int(uptime_s.split()[0]) if uptime_s else None
    load_1m = None
    if load_s:
        try:
            load_1m = float(load_s.split()[0])
        except (ValueError, IndexError):
            load_1m = None
    mem_used_pct = None
    mem_lines = [m for m in mem_s.splitlines() if m]
    if len(mem_lines) >= 2:
        total = _int(mem_lines[0])
        avail = _int(mem_lines[1])
        if total:
            mem_used_pct = round((total - avail) / total * 100, 1)
    fw_ts = _int(fw_s) if fw_s else None

    return {
        "active_core": core or None,
        "uptime_seconds": uptime,
        "cpu_load_1m": load_1m,
        "memory_used_percent": mem_used_pct,
        "firmware_timestamp": fw_ts,
    }


class MisterSSH:
    """Maintains a persistent asyncssh connection and runs the probe."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._conn = None

    async def _ensure(self) -> None:
        if self._conn is not None:
            return
        import asyncssh

        self._conn = await asyncssh.connect(
            self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            known_hosts=None,
        )

    async def async_probe(self) -> dict:
        """Run the probe; returns {} on any failure (SSH is best-effort)."""
        from .const import SSH_PROBE_CMD

        try:
            await self._ensure()
            result = await self._conn.run(SSH_PROBE_CMD, check=False, timeout=10)
            return parse_ssh_probe(result.stdout or "")
        except Exception as err:  # noqa: BLE001 - asyncssh raises many types; SSH is best-effort and must never break the HTTP integration
            _LOGGER.debug("MiSTer SSH probe failed: %s", err)
            self._conn = None
            return {}

    async def async_close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
