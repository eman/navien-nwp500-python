"""
Data models for NaviLink devices and responses.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DeviceFeatures:
    """Device feature capabilities and specifications."""

    country_code: int
    model_type_code: int
    control_type_code: int
    volume_code: int
    controller_sw_version: int
    panel_sw_version: int
    wifi_sw_version: int
    controller_sw_code: int
    panel_sw_code: int
    wifi_sw_code: int
    controller_serial_number: str
    power_use: int
    holiday_use: int
    program_reservation_use: int
    dhw_use: int
    dhw_temperature_setting_use: int
    dhw_temperature_min: int
    dhw_temperature_max: int
    smart_diagnostic_use: int
    wifi_rssi_use: int
    temperature_type: int
    temp_formula_type: int
    energy_usage_use: int
    freeze_protection_use: int
    freeze_protection_temp_min: int
    freeze_protection_temp_max: int
    mixing_value_use: int
    dr_setting_use: int
    anti_legionella_setting_use: int
    hpwh_use: int
    dhw_refill_use: int
    eco_use: int
    electric_use: int
    heatpump_use: int
    energy_saver_use: int
    high_demand_use: int


@dataclass
class DeviceStatus:
    """Current device status and sensor readings."""

    command: int
    outside_temperature: int
    special_function_status: int
    did_reload: int
    error_code: int
    sub_error_code: int
    operation_mode: int
    operation_busy: int
    freeze_protection_use: int
    dhw_use: int
    dhw_use_sustained: int
    dhw_temperature: int
    dhw_temperature_setting: int
    program_reservation_use: int
    smart_diagnostic: int
    fault_status1: int
    fault_status2: int
    wifi_rssi: int
    eco_use: int
    dhw_target_temperature_setting: int
    tank_upper_temperature: int
    tank_lower_temperature: int
    discharge_temperature: int
    suction_temperature: int
    evaporator_temperature: int
    ambient_temperature: int
    target_super_heat: int
    comp_use: int
    eev_use: int
    eva_fan_use: int
    current_inst_power: int
    shut_off_valve_use: int
    con_ovr_sensor_use: int
    wtr_ovr_sensor_use: int
    dhw_charge_per: int
    dr_event_status: int
    vacation_day_setting: int
    vacation_day_elapsed: int
    freeze_protection_temperature: int
    anti_legionella_use: int
    anti_legionella_period: int
    anti_legionella_operation_busy: int
    program_reservation_type: int
    dhw_operation_setting: int
    temperature_type: int
    temp_formula_type: int
    error_buzzer_use: int
    current_heat_use: int
    current_inlet_temperature: int
    current_statenum: int
    target_fan_rpm: int
    current_fan_rpm: int
    fan_pwm: int
    dhw_temperature2: int
    current_dhw_flow_rate: int
    mixing_rate: int
    eev_step: int
    current_super_heat: int
    heat_upper_use: int
    heat_lower_use: int
    scald_use: int
    air_filter_alarm_use: int
    air_filter_alarm_period: int
    air_filter_alarm_elapsed: int
    cumulated_op_time_eva_fan: int
    cumulated_dhw_flow_rate: int
    tou_status: int
    hp_upper_on_temp_setting: int
    hp_upper_off_temp_setting: int
    hp_lower_on_temp_setting: int
    hp_lower_off_temp_setting: int
    he_upper_on_temp_setting: int
    he_upper_off_temp_setting: int
    he_lower_on_temp_setting: int
    he_lower_off_temp_setting: int
    hp_upper_on_diff_temp_setting: int
    hp_upper_off_diff_temp_setting: int
    hp_lower_on_diff_temp_setting: int
    hp_lower_off_diff_temp_setting: int
    he_upper_on_diff_temp_setting: int
    he_upper_off_diff_temp_setting: int
    he_lower_on_tdiffemp_setting: int
    he_lower_off_diff_temp_setting: int
    dr_override_status: int
    tou_override_status: int
    total_energy_capacity: int
    available_energy_capacity: int
    # Additional convenience fields for enhanced monitoring
    heat_pump_status: Optional[int] = 0  # Heat pump operational status
    resistance_heater_status: Optional[int] = 0  # Resistance heater status
    defrost_mode: Optional[int] = 0  # Defrost mode active


@dataclass
class DeviceInfo:
    """Device information and metadata."""

    device_type: int
    mac_address: str
    additional_value: str
    controller_serial_number: str
    features: DeviceFeatures


@dataclass
class Reservation:
    """Device reservation/schedule entry."""

    id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    temperature: Optional[int] = None
    enabled: Optional[bool] = None
    recurring: Optional[bool] = None
    days_of_week: Optional[List[int]] = None


@dataclass
class TOUInfo:
    """Time of Use information."""

    status: Optional[int] = None
    schedule: Optional[List[Dict[str, Any]]] = None
    rates: Optional[List[Dict[str, Any]]] = None


@dataclass
class UserInfo:
    """User account information."""

    user_id: str
    email: str
    user_type: str
    group_id: Optional[str] = None
    session_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None


@dataclass
class EnergyUsage:
    """Energy usage data."""

    date: str
    usage: float
    cost: Optional[float] = None
    period_type: str = "daily"  # daily, monthly, yearly
