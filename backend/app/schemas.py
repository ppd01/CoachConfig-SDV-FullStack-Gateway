from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, model_validator


class PowertrainType(str, Enum):
    BEV = "BEV"
    FCEV = "FCEV"


class CoolingStrategy(str, Enum):
    CHILLER_ACTIVE = "CHILLER_ACTIVE"
    PASSIVE_RADIATOR = "PASSIVE_RADIATOR"
    HEAT_PUMP_COUPLED = "HEAT_PUMP_COUPLED"


class TractionBatteryConfig(BaseModel):
    chemistry: str = Field(..., description="e.g., LFP, NMC High-Energy")
    installed_capacity_kwh: float = Field(..., gt=50.0, le=1000.0, description="Gross capacity (kWh)")
    usable_soc_min_pct: float = Field(10.0, ge=5.0, le=20.0)
    usable_soc_max_pct: float = Field(90.0, ge=80.0, le=100.0)
    max_continuous_discharge_kw: float = Field(..., gt=0.0, le=800.0)
    max_recup_power_kw: float = Field(..., gt=0.0, le=500.0)
    cell_temp_derate_start_c: float = Field(45.0, ge=35.0, le=60.0)
    cell_temp_shutdown_c: float = Field(55.0, ge=50.0, le=75.0)


class InverterDriveConfig(BaseModel):
    inverter_type: str = Field(..., description="e.g., SiC Dual-Inverter")
    max_traction_power_kw: float = Field(..., gt=100.0, le=800.0)
    continuous_power_kw: float = Field(..., gt=50.0, le=600.0)
    max_torque_nm: float = Field(..., gt=500.0, le=6000.0)
    dc_bus_voltage_nominal_v: float = Field(..., ge=600.0, le=950.0)


class FuelCellSystemConfig(BaseModel):
    stack_net_power_kw: float = Field(..., gt=50.0, le=400.0)
    h2_storage_capacity_kg: float = Field(..., gt=10.0, le=100.0)
    tank_pressure_bar: float = Field(350.0, description="350 or 700 bar")
    operating_temp_c: float = Field(75.0, ge=60.0, le=95.0)
    min_startup_temp_c: float = Field(-25.0, le=0.0)


class HvacThermalConfig(BaseModel):
    passenger_heating_max_kw: float = Field(..., gt=0.0, le=60.0)
    passenger_cooling_max_kw: float = Field(..., gt=0.0, le=45.0)
    battery_cooling_strategy: CoolingStrategy = CoolingStrategy.HEAT_PUMP_COUPLED
    cabin_target_temp_c: float = Field(21.0, ge=16.0, le=26.0)
    preconditioning_allowed_on_battery: bool = Field(False)


class CoachConfiguration(BaseModel):
    config_id: str = Field(..., description="Unique calibration ID, e.g., SETRA-S515-BEV")
    variant_name: str = Field(..., description="Model series, e.g., Setra S 515 HD eCoach")
    powertrain_type: PowertrainType
    gross_vehicle_weight_rating_kg: float = Field(..., ge=12000.0, le=26000.0)
    traction_battery: TractionBatteryConfig
    inverter_drive: InverterDriveConfig
    fuel_cell: Optional[FuelCellSystemConfig] = None
    hvac_thermal: HvacThermalConfig
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def verify_fcev_requirements(self) -> "CoachConfiguration":
        if self.powertrain_type == PowertrainType.FCEV and self.fuel_cell is None:
            raise ValueError("Powertrain configured as FCEV requires 'fuel_cell' calibration profile.")
        if self.powertrain_type == PowertrainType.BEV and self.fuel_cell is not None:
            raise ValueError("BEV variant cannot have 'fuel_cell' system configured.")
        return self


class ConfigDiffItem(BaseModel):
    parameter_path: str
    variant_a_val: Any
    variant_b_val: Any
    category: str
    impact_level: str = Field("INFO", description="INFO, WARN, CRITICAL")


class ConfigDiffResponse(BaseModel):
    variant_a_id: str
    variant_b_id: str
    differences_count: int
    differences: List[ConfigDiffItem]


class ValidationIssue(BaseModel):
    severity: str = Field(..., description="WARNING or ERROR")
    rule: str
    message: str
    suggested_action: str


class ValidationReport(BaseModel):
    config_id: str
    is_valid_for_deployment: bool
    issues: List[ValidationIssue]