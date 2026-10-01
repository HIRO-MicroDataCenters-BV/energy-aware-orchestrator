"""
Modbus grid client - polls one or more Modbus TCP PDU units for live Inlet
power and turns it into a grid supply slot.

Topology: a cluster of daisy-chained PDUs is served by a single Modbus TCP
connection - the Main (or standalone) PDU's address. Link PDUs don't answer
Modbus requests themselves; their own inlet registers are reached *through*
the Main PDU using their own unit/slave id. There is no aggregation on the
PDU side - each unit id's inlet reading covers only that one PDU - so the
cluster total is summed here, client-side.

Only unit_ids=[1] (a single, standalone PDU) is verified as of this writing;
polling additional unit ids (cluster mode) is best-effort - a bad or
unreachable unit id is logged and skipped rather than failing the whole
poll cycle. See _read_unit()/ERROR_DEVICE_STATES for the per-unit health
check, encoded as a signed 16-bit value (e.g. -2 = 0xFFFE).

The register layout mirrors modbus/src/register/elements.rs as of tag
v1.4.1-1, matching the vendor's read_pdu.py reference script.
"""

import asyncio
import logging
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.services.grid_clients.base import GridSourceClient

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_NAME = "modbus-pdu"

# --- Inlet block layout (elements.rs @ v1.4.1-1, same as read_pdu.py) ------
INLET_START = 15
INLET_DEVICE_STATE_OFFSET = 0   # block's own "start address" register - see
                                 # module docstring: Offline/Connection Lost/
                                 # On/Off/Unknown Error
INLET_ACTIVE_POWER_OFFSET = 4   # 1 W resolution
INLET_READ_LENGTH = 5           # covers offsets 0..4

# Two's-complement 16-bit encodings of the sheet's documented bad states.
# On(0) and Off(1) are left out deliberately - both are legitimate device
# states (a deliberately-off outlet/inlet still gives a trustworthy ~0W
# reading), not reasons to discard the reading.
ERROR_DEVICE_STATES = {
    0xFFFF: "Offline(-1)",
    0xFFFE: "Connection Lost(-2)",
    0xFF80: "Unknown Error(-128)",
}


class ModbusError(Exception):
    pass


class AsyncModbusTcpClient:
    """Minimal async Modbus TCP master: function code 3 (read holding registers).

    Mirrors the protocol in the vendor's read_pdu.py, using asyncio streams
    instead of a blocking socket so a slow/unreachable PDU never blocks the
    event loop the rest of this service runs on.
    """

    MAX_REGS_PER_REQUEST = 125

    def __init__(self, host: str, port: int = 502, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._tid = 0
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def connect(self):
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=self.timeout
        )

    async def close(self):
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def _recv_exactly(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = await asyncio.wait_for(self._reader.read(n - len(buf)), timeout=self.timeout)
            if not chunk:
                raise ModbusError("connection closed by PDU")
            buf += chunk
        return buf

    async def read_holding(self, address: int, count: int, unit_id: int) -> List[int]:
        """Read `count` holding registers starting at `address` for the given unit id."""
        out: List[int] = []
        while count > 0:
            n = min(count, self.MAX_REGS_PER_REQUEST)
            out.extend(await self._read_chunk(address, n, unit_id))
            address += n
            count -= n
        return out

    async def _read_chunk(self, address: int, count: int, unit_id: int) -> List[int]:
        self._tid = (self._tid + 1) & 0xFFFF
        pdu = struct.pack(">BHH", 3, address, count)
        adu = struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, unit_id) + pdu
        self._writer.write(adu)
        await asyncio.wait_for(self._writer.drain(), timeout=self.timeout)

        _tid, _proto, length, _unit = struct.unpack(">HHHB", await self._recv_exactly(7))
        body = await self._recv_exactly(length - 1)
        func = body[0]
        if func & 0x80:
            raise ModbusError(
                f"exception code {body[1]} for unit {unit_id}, address {address}, count {count}"
            )
        byte_count = body[1]
        data = body[2:2 + byte_count]
        return list(struct.unpack(">%dH" % (byte_count // 2), data))


@dataclass
class UnitReading:
    unit_id: int
    active_power_watts: Optional[float]
    error: Optional[str] = None


class ModbusGridClient(GridSourceClient):
    """
    Reads live Inlet Active Power from one or more Modbus TCP PDU units and
    turns it into a single grid-supply slot per poll cycle.

    mode="reading" (default) stores the summed Inlet Active Power as-is -
    this is actual power currently flowing, not spare capacity. mode=
    "headroom" instead stores (rated_capacity_watts - summed power); the PDU
    has no register for a capacity/breaker rating, so rated_capacity_watts
    must be supplied via config, and headroom mode silently falls back to
    reading mode if it isn't.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 502,
        unit_ids: Optional[List[int]] = None,
        mode: str = "reading",
        rated_capacity_watts: Optional[float] = None,
        poll_interval_seconds: int = 300,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        energy_source_type: str = "grid",
        timeout: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.unit_ids = unit_ids or [1]
        self.mode = mode
        self.rated_capacity_watts = rated_capacity_watts
        self.poll_interval_seconds = poll_interval_seconds
        self.provider_name = provider_name
        self.energy_source_type = energy_source_type
        self.timeout = timeout

        if self.mode == "headroom" and rated_capacity_watts is None:
            logger.warning(
                "ModbusGridClient: mode='headroom' but no rated_capacity_watts "
                "configured - falling back to 'reading' mode until one is set."
            )
            self.mode = "reading"

        if len(self.unit_ids) > 1:
            logger.warning(
                f"ModbusGridClient: polling {len(self.unit_ids)} unit ids "
                f"{self.unit_ids} - cluster reads are not yet verified by the "
                "PDU vendor; start with a single unit id in production."
            )

        logger.info(
            f"ModbusGridClient initialized (host: {host}, port: {port}, "
            f"unit_ids: {self.unit_ids}, mode: {self.mode})"
        )

    async def fetch_grid_capacity(self) -> Optional[List[Dict[str, Any]]]:
        if not self.host:
            logger.debug("No Modbus host configured, skipping PDU poll")
            return None

        readings = await self._read_all_units()
        good = [r for r in readings if r.error is None and r.active_power_watts is not None]

        if not good:
            logger.warning(f"ModbusGridClient: no usable readings from any of {self.unit_ids}")
            return None

        if len(good) < len(readings):
            skipped = [r.unit_id for r in readings if r.error is not None]
            logger.warning(f"ModbusGridClient: skipped unit id(s) {skipped} this cycle")

        total_watts = sum(r.active_power_watts for r in good)
        available_watts = (
            self.rated_capacity_watts - total_watts if self.mode == "headroom" else total_watts
        )
        # Real meter reading, not a prediction - full confidence when every
        # configured unit answered, scaled down if some were skipped so a
        # partial cluster read doesn't look as trustworthy as a full one.
        confidence_percentage = 100.0 * len(good) / len(self.unit_ids)

        now = datetime.now(timezone.utc)
        slot_end = now + timedelta(seconds=self.poll_interval_seconds)

        logger.info(
            f"ModbusGridClient: {len(good)}/{len(self.unit_ids)} unit(s) read, "
            f"total {total_watts:.1f} W, available_watts={available_watts:.1f} "
            f"({self.mode} mode)"
        )

        return [{
            "provider_name": self.provider_name,
            "slot_start_time": now.isoformat(),
            "slot_end_time": slot_end.isoformat(),
            "available_watts": available_watts,
            "energy_source_type": self.energy_source_type,
            "confidence_percentage": confidence_percentage,
        }]

    async def _read_all_units(self) -> List[UnitReading]:
        try:
            async with AsyncModbusTcpClient(self.host, self.port, self.timeout) as client:
                return [await self._read_unit(client, unit_id) for unit_id in self.unit_ids]
        except (OSError, asyncio.TimeoutError, ModbusError) as e:
            logger.warning(f"ModbusGridClient: could not connect to {self.host}:{self.port}: {e}")
            return [
                UnitReading(unit_id=u, active_power_watts=None, error=str(e))
                for u in self.unit_ids
            ]

    async def _read_unit(self, client: AsyncModbusTcpClient, unit_id: int) -> UnitReading:
        try:
            regs = await client.read_holding(INLET_START, INLET_READ_LENGTH, unit_id)
            device_state = regs[INLET_DEVICE_STATE_OFFSET]
            if device_state in ERROR_DEVICE_STATES:
                return UnitReading(
                    unit_id=unit_id,
                    active_power_watts=None,
                    error=f"device state {ERROR_DEVICE_STATES[device_state]} (raw 0x{device_state:04X})",
                )
            active_power = float(regs[INLET_ACTIVE_POWER_OFFSET])
            return UnitReading(unit_id=unit_id, active_power_watts=active_power)
        except (ModbusError, IndexError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"ModbusGridClient: unit {unit_id} read failed: {e}")
            return UnitReading(unit_id=unit_id, active_power_watts=None, error=str(e))
