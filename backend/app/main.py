import os
import yaml
import asyncio
from typing import Dict, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    CoachConfiguration,
    ConfigDiffResponse,
    ConfigDiffItem,
    ValidationReport,
    ValidationIssue,
)
from app.core.bus_manager import can_reader_task, get_latest_telemetry

app = FastAPI(
    title="CoachConfig-AI Backend",
    version="1.0.0",
    description="Next-Gen Coach Configuration & Operational Strategy Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CALIBRATION_STORE: Dict[str, CoachConfiguration] = {}
CALIBRATION_DIR = os.path.join(os.path.dirname(__file__), "data", "calibrations")
can_task_handle = None


def load_seed_calibrations():
    if not os.path.exists(CALIBRATION_DIR):
        os.makedirs(CALIBRATION_DIR, exist_ok=True)
        return

    for filename in os.listdir(CALIBRATION_DIR):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(CALIBRATION_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_data = yaml.safe_load(f)
                    config = CoachConfiguration(**raw_data)
                    CALIBRATION_STORE[config.config_id] = config
                    print(f"[Loaded] Calibration: {config.config_id}")
            except Exception as e:
                print(f"[Warning] Failed loading {filename}: {e}")


@app.on_event("startup")
async def startup_event():
    load_seed_calibrations()
    # Spawn background SocketCAN listener on vcan0
    global can_task_handle
    can_task_handle = asyncio.create_task(can_reader_task(channel="vcan0"))


@app.on_event("shutdown")
async def shutdown_event():
    global can_task_handle
    if can_task_handle:
        can_task_handle.cancel()


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ONLINE",
        "node": "Raspberry Pi 5 Gateway",
        "loaded_configs_count": len(CALIBRATION_STORE),
        "latest_telemetry": get_latest_telemetry(),
    }


@app.get("/api/v1/configs", response_model=List[CoachConfiguration], tags=["Configurations"])
async def list_configurations():
    return list(CALIBRATION_STORE.values())


@app.get("/api/v1/configs/{config_id}", response_model=CoachConfiguration, tags=["Configurations"])
async def get_configuration(config_id: str):
    if config_id not in CALIBRATION_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found.",
        )
    return CALIBRATION_STORE[config_id]


@app.post(
    "/api/v1/configs",
    response_model=CoachConfiguration,
    status_code=status.HTTP_201_CREATED,
    tags=["Configurations"],
)
async def ingest_configuration(config: CoachConfiguration):
    CALIBRATION_STORE[config.config_id] = config
    return config


def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@app.get("/api/v1/diff", response_model=ConfigDiffResponse, tags=["Analytics"])
async def diff_configurations(variant_a_id: str, variant_b_id: str):
    load_seed_calibrations()  # <-- Reload fresh files from disk
    if variant_a_id not in CALIBRATION_STORE:
        raise HTTPException(status_code=404, detail=f"Variant {variant_a_id} not found.")
    if variant_b_id not in CALIBRATION_STORE:
        raise HTTPException(status_code=404, detail=f"Variant {variant_b_id} not found.")

    flat_a = _flatten_dict(CALIBRATION_STORE[variant_a_id].model_dump())
    flat_b = _flatten_dict(CALIBRATION_STORE[variant_b_id].model_dump())

    all_keys = sorted(set(flat_a.keys()).union(set(flat_b.keys())))
    diffs: List[ConfigDiffItem] = []

    for key in all_keys:
        val_a = flat_a.get(key)
        val_b = flat_b.get(key)

        if val_a != val_b:
            category = key.split(".")[0]
            impact = "INFO"
            if "max_traction_power" in key or "max_continuous_discharge" in key:
                impact = "CRITICAL"
            elif "cooling" in key or "heating" in key:
                impact = "WARN"

            diffs.append(
                ConfigDiffItem(
                    parameter_path=key,
                    variant_a_val=val_a,
                    variant_b_val=val_b,
                    category=category,
                    impact_level=impact,
                )
            )

    return ConfigDiffResponse(
        variant_a_id=variant_a_id,
        variant_b_id=variant_b_id,
        differences_count=len(diffs),
        differences=diffs,
    )


@app.get("/api/v1/validate/{config_id}", response_model=ValidationReport, tags=["Analytics"])
async def validate_configuration(config_id: str):
    load_seed_calibrations()  # <-- Reload fresh files from disk
    if config_id not in CALIBRATION_STORE:
        raise HTTPException(status_code=404, detail=f"Variant {config_id} not found.")

    cfg = CALIBRATION_STORE[config_id]
    issues: List[ValidationIssue] = []

    if cfg.inverter_drive.max_traction_power_kw > cfg.traction_battery.max_continuous_discharge_kw:
        issues.append(
            ValidationIssue(
                severity="ERROR",
                rule="POWER_DRAW_EXCEEDS_DISCHARGE_MARGIN",
                message=(
                    f"Inverter peak traction power ({cfg.inverter_drive.max_traction_power_kw} kW) "
                    f"exceeds battery continuous discharge limit ({cfg.traction_battery.max_continuous_discharge_kw} kW)."
                ),
                suggested_action="Verify DC bus derating timers in inverter parameter map.",
            )
        )

    if cfg.powertrain_type == "FCEV" and cfg.fuel_cell:
        if cfg.fuel_cell.min_startup_temp_c > -20.0:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    rule="SUBZERO_H2_STARTUP_LIMITATION",
                    message=(
                        f"Fuel cell cold startup limit is {cfg.fuel_cell.min_startup_temp_c}°C, "
                        "which is above target Scandinavian winter testing limits (-25°C)."
                    ),
                    suggested_action="Add auxiliary pre-heater circuit to fuel cell cooling jacket.",
                )
            )

    has_fatal_errors = any(issue.severity in ["ERROR", "CRITICAL"] for issue in issues)

    return ValidationReport(
        config_id=config_id,
        is_valid_for_deployment=not has_fatal_errors,
        issues=issues,
    )


# WebSocket Streamer for live vehicle telemetry
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Broadcast the latest decoded CAN frame state at 10 Hz
            payload = get_latest_telemetry()
            await websocket.send_json(payload)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass