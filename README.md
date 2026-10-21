# CoachConfig-AI: In-Vehicle SDV Gateway & Variant Platform

**Proof-of-Concept for Next-Gen Electric & Hydrogen Coach Architectures (Daimler Buses / Setra)**  
*Hardware Platform: Raspberry Pi 5 (Edge Gateway Node)*

---

## 1. System Overview

CoachConfig-AI models a Centralized Vehicle Computer (HPC) edge gateway inside a Software-Defined Vehicle (SDV) architecture. It validates calibrations, analyzes variant deltas between Battery Electric (BEV) and Hydrogen Fuel-Cell (FCEV) Setra coaches, and processes live vehicle bus telemetry streamed over Linux SocketCAN.

### Key Architectural Pillars
- **In-Vehicle CAN Bus (SocketCAN):** Simulates low-level powertrain communication across virtual bus `vcan0` adhering to CAN 2.0B / CAN FD frame conventions.
- **Microservices & Adaptive AUTOSAR Alignment:** FastAPI backend running async event loops (`bus_manager.py`) to decode binary frames into engineering parameters without polling delays.
- **Configuration & Calibration Management:** Pydantic v2 schemas enforcing physical boundary limits (continuous discharge margins, thermal envelope derating thresholds, H2 cold-startup boundaries).
- **Edge UI (Vite + React + Tailwind):** Operator dashboard rendering live bus telemetry over full-duplex WebSockets alongside parameter delta inspection.

---

## 2. Telemetry Bus Protocol (`vcan0`)

| CAN ID | Subsystem | Raw Layout | Decoded Signals |
| :--- | :--- | :--- | :--- |
| `0x180` | Battery System | `>HHhh` (8 bytes) | SoC (%), DC Voltage (V), Current (A), Cell Temp (°C) |
| `0x181` | Traction Inverter | `>HhHH` (8 bytes) | Vehicle Speed (km/h), Motor Torque (Nm), Inverter Power (kW) |
| `0x182` | HVAC Thermal | `>hHB3s` (8 bytes) | Cabin Temp (°C), Aux HVAC Draw (kW), Derate Active Flag |

---

## 3. Quickstart & Deployment

### One-Command Master Startup
```bash
cd ~/coachconfig-ai
./run_poc.sh