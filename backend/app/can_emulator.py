import can
import time
import math
import struct

# Standard CAN arbitration IDs for simulated powertrain units
CAN_ID_BATTERY_STATUS = 0x180   # Battery SoC, Voltage, Current, Cell Temp
CAN_ID_TRACTION_STATUS = 0x181  # Vehicle Speed, Motor Torque, Inverter Power
CAN_ID_HVAC_STATUS     = 0x182  # Cabin Temp, HVAC Aux Power, Derate Flag


def run_emulator(channel="vcan0"):
    print(f"[*] Starting Powertrain CAN Emulator on {channel}...")
    bus = can.interface.Bus(channel=channel, interface="socketcan")

    soc = 92.0
    t = 0.0

    try:
        while True:
            # Simulated mission driving dynamics (highway cruising + grade changes)
            speed_kmh = max(0.0, 85.0 + 15.0 * math.sin(t / 10.0))
            traction_kw = max(0.0, 180.0 + 90.0 * math.sin(t / 8.0))
            hvac_kw = 22.5 + 2.5 * math.cos(t / 15.0)
            cell_temp_c = 32.0 + 8.0 * (1.0 - math.exp(-t / 60.0)) + 3.0 * math.sin(t / 12.0)

            # Energy depletion rate based on combined traction + auxiliary draw
            total_draw_kw = traction_kw + hvac_kw
            soc = max(5.0, soc - (total_draw_kw / 588.0) * (0.1 / 3600.0) * 100.0)

            # 1. Pack Frame: Battery Status (ID: 0x180)
            # Layout: soc*10 (uint16), voltage*10 (uint16), current*10 (int16), temp*10 (int16)
            voltage_v = 750.0 - (1.0 - (soc / 100.0)) * 40.0
            current_a = (total_draw_kw * 1000.0) / max(1.0, voltage_v)
            data_batt = struct.pack(
                ">HHhh",
                int(soc * 10),
                int(voltage_v * 10),
                int(current_a * 10),
                int(cell_temp_c * 10),
            )
            bus.send(can.Message(arbitration_id=CAN_ID_BATTERY_STATUS, data=data_batt, is_extended_id=False))

            # 2. Pack Frame: Traction Status (ID: 0x181)
            # Layout: speed*10 (uint16), torque (int16), power*10 (uint16), reserved (uint16)
            torque_nm = int((traction_kw * 9550.0) / max(10.0, (speed_kmh * 15.0)))
            data_trac = struct.pack(
                ">HhHH",
                int(speed_kmh * 10),
                int(min(3100, max(-3100, torque_nm))),
                int(traction_kw * 10),
                0,
            )
            bus.send(can.Message(arbitration_id=CAN_ID_TRACTION_STATUS, data=data_trac, is_extended_id=False))

            # 3. Pack Frame: HVAC Thermal Status (ID: 0x182)
            # Layout: cabin_temp*10 (int16), hvac_power*10 (uint16), derate_active (uint8), reserved (3 bytes)
            derate_flag = 1 if cell_temp_c >= 45.0 else 0
            data_hvac = struct.pack(
                ">hHB3s",
                int(21.0 * 10),
                int(hvac_kw * 10),
                derate_flag,
                b"\x00\x00\x00",
            )
            bus.send(can.Message(arbitration_id=CAN_ID_HVAC_STATUS, data=data_hvac, is_extended_id=False))

            t += 0.2
            time.sleep(0.2)  # Broadcast at 5 Hz
    except KeyboardInterrupt:
        print("\n[!] CAN Emulator halted.")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    run_emulator()