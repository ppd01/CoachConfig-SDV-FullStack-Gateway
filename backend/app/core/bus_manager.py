import can
import struct
import asyncio
from typing import Dict, Any

# Current decoded state of vehicle telemetry
telemetry_state: Dict[str, Any] = {
    "soc_pct": 0.0,
    "dc_voltage_v": 0.0,
    "dc_current_a": 0.0,
    "cell_temp_c": 0.0,
    "vehicle_speed_kmh": 0.0,
    "motor_torque_nm": 0,
    "traction_power_kw": 0.0,
    "cabin_temp_c": 0.0,
    "hvac_power_kw": 0.0,
    "thermal_derate_active": False,
}

_running = False


def decode_can_frame(msg: can.Message):
    """Parses binary payload into engineering units."""
    global telemetry_state

    if msg.arbitration_id == 0x180 and len(msg.data) >= 8:
        # Layout: uint16 soc*10, uint16 volt*10, int16 curr*10, int16 temp*10
        soc, volt, curr, temp = struct.unpack(">HHhh", msg.data[:8])
        telemetry_state["soc_pct"] = round(soc / 10.0, 2)
        telemetry_state["dc_voltage_v"] = round(volt / 10.0, 1)
        telemetry_state["dc_current_a"] = round(curr / 10.0, 1)
        telemetry_state["cell_temp_c"] = round(temp / 10.0, 1)

    elif msg.arbitration_id == 0x181 and len(msg.data) >= 8:
        # Layout: uint16 speed*10, int16 torque, uint16 power*10, uint16 reserved
        spd, trq, pwr, _ = struct.unpack(">HhHH", msg.data[:8])
        telemetry_state["vehicle_speed_kmh"] = round(spd / 10.0, 1)
        telemetry_state["motor_torque_nm"] = trq
        telemetry_state["traction_power_kw"] = round(pwr / 10.0, 1)

    elif msg.arbitration_id == 0x182 and len(msg.data) >= 4:
        # Layout: int16 cabin_temp*10, uint16 hvac_power*10, uint8 derate_flag
        cab_t, hvac_p, derate = struct.unpack(">hHB", msg.data[:5])
        telemetry_state["cabin_temp_c"] = round(cab_t / 10.0, 1)
        telemetry_state["hvac_power_kw"] = round(hvac_p / 10.0, 1)
        telemetry_state["thermal_derate_active"] = bool(derate)


async def can_reader_task(channel="vcan0"):
    """Background task reading SocketCAN and updating internal telemetry state."""
    global _running
    _running = True
    print(f"[*] Initializing SocketCAN listener on {channel}...")

    try:
        bus = can.interface.Bus(channel=channel, interface="socketcan")
    except Exception as e:
        print(f"[!] Failed to bind to {channel}: {e}")
        return

    loop = asyncio.get_running_loop()

    try:
        while _running:
            # Read non-blocking using executor so the async loop isn't stalled
            msg = await loop.run_in_executor(None, bus.recv, 0.5)
            if msg:
                decode_can_frame(msg)
    except asyncio.CancelledError:
        pass
    finally:
        bus.shutdown()
        print("[*] SocketCAN listener closed.")


def get_latest_telemetry() -> Dict[str, Any]:
    return telemetry_state.copy()