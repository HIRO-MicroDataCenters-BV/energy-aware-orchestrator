"""
Dev/test-only mock Modbus PDU server. Stands in for a real Modbus TCP PDU so
ModbusGridClient can be exercised without one - the Modbus counterpart to
grid_stub.py's HTTP stand-in. Never intended for production use.

Serves function-code-3 (read holding registers) requests for the Inlet
block (address 15, 5 registers: device state, status, current, peak
current, active power - matching app/services/grid_clients/modbus_client.py)
for whichever unit ids have been configured via the control HTTP API. A
request for an unconfigured unit id gets a real Modbus exception response,
so this also exercises ModbusGridClient's skip-on-error path.

Control API (HTTP, port 8080):
  POST /pdu/<unit_id>  {"device_state": 0, "active_power_watts": 950}
  GET  /pdu/<unit_id>  -> current fake reading for that unit id
  GET  /pdu            -> all configured units

device_state follows the register sheet's enum: 0 = On, 1 = Off,
-1 = Offline, -2 = Connection Lost, -128 = Unknown Error. Pass the signed
value, e.g. -2 for Connection Lost - it's encoded on the wire as two's
complement automatically.

Defaults to one healthy unit (id 1, 1000 W) so a poll works out of the box.
"""

import asyncio
import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

INLET_START = 15
INLET_READ_LENGTH = 5
INLET_DEVICE_STATE_OFFSET = 0
INLET_ACTIVE_POWER_OFFSET = 4

# unit_id -> {"device_state": int, "active_power_watts": float}
state = {1: {"device_state": 0, "active_power_watts": 1000.0}}
state_lock = threading.Lock()


def _to_u16(signed_value: int) -> int:
    return signed_value & 0xFFFF


class ControlHandler(BaseHTTPRequestHandler):
    def _unit_id_from_path(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "pdu":
            try:
                return int(parts[1])
            except ValueError:
                return None
        return None

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        with state_lock:
            if self.path == "/pdu":
                self._send_json(200, state)
                return
            unit_id = self._unit_id_from_path()
            if unit_id is None or unit_id not in state:
                self.send_response(404)
                self.end_headers()
                return
            self._send_json(200, state[unit_id])

    def do_POST(self):
        unit_id = self._unit_id_from_path()
        if unit_id is None:
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
            with state_lock:
                state[unit_id] = {
                    "device_state": int(data.get("device_state", 0)),
                    "active_power_watts": float(data.get("active_power_watts", 0.0)),
                }
                result = dict(state[unit_id])
            self._send_json(200, {"status": "ok", "unit_id": unit_id, **result})
        except Exception as e:
            body = str(e).encode()
            self.send_response(400)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format, *args):
        pass


async def handle_modbus(reader, writer):
    try:
        while True:
            header = await reader.readexactly(7)
            tid, proto, length, unit_id = struct.unpack(">HHHB", header)
            body = await reader.readexactly(length - 1)
            func, address, count = struct.unpack(">BHH", body)

            with state_lock:
                unit = state.get(unit_id)

            if func != 3 or unit is None:
                # Modbus exception: illegal data address / slave device failure
                resp_pdu = struct.pack(">BB", func | 0x80, 0x02)
            else:
                regs = [0] * count
                device_state_addr = INLET_START + INLET_DEVICE_STATE_OFFSET
                active_power_addr = INLET_START + INLET_ACTIVE_POWER_OFFSET
                if address <= device_state_addr < address + count:
                    regs[device_state_addr - address] = _to_u16(unit["device_state"])
                if address <= active_power_addr < address + count:
                    regs[active_power_addr - address] = int(unit["active_power_watts"])
                data = b"".join(struct.pack(">H", r) for r in regs)
                resp_pdu = struct.pack(">BB", func, len(data)) + data

            adu = struct.pack(">HHHB", tid, 0, len(resp_pdu) + 1, unit_id) + resp_pdu
            writer.write(adu)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        writer.close()


async def run_modbus_server(port: int):
    server = await asyncio.start_server(handle_modbus, "0.0.0.0", port)
    async with server:
        await server.serve_forever()


def run_control_server(port: int):
    ThreadingHTTPServer(("0.0.0.0", port), ControlHandler).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=run_control_server, args=(8080,), daemon=True).start()
    asyncio.run(run_modbus_server(502))
