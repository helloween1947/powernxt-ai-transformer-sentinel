"""Validated API inputs and one canonical measurement vocabulary."""
import math
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CHANNELS = (
    'voltage_r_v', 'voltage_y_v', 'voltage_b_v',
    'current_r_a', 'current_y_a', 'current_b_a',
    'oil_temperature_c', 'ambient_temperature_c', 'oil_level_pct',
)
SCENARIOS = Literal['normal', 'overload', 'overheating', 'low_oil', 'phase_imbalance', 'undervoltage']

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, str_strip_whitespace=True)

class Limits(Input):
    max_load_pct: float = Field(default=120, gt=0, le=300)
    max_top_oil_temp_c: float = Field(default=105, ge=0, le=200)
    min_oil_level_pct: float = Field(default=60, ge=0, le=100)
    max_current_imbalance_pct: float = Field(default=10, gt=0, le=100)
    min_voltage_pu: float = Field(default=.9, gt=0)
    max_voltage_pu: float = Field(default=1.1, gt=0)

    @model_validator(mode='after')
    def ordered_voltage(self):
        if self.min_voltage_pu >= self.max_voltage_pu:
            raise ValueError('Minimum voltage limit must be below maximum.')
        return self

class Configuration(Input):
    rated_kva: float = Field(default=1000, ge=.001, le=1000000)
    rated_voltage_v: float = Field(default=11000, ge=1, le=800000)
    operational_limits: Limits = Field(default_factory=Limits)
    oil_time_constant_s: float = Field(default=1800, gt=0, le=86400)
    rated_top_oil_rise_c: float = Field(default=55, gt=0, le=150)

    @model_validator(mode='after')
    def bounded_rating(self):
        current = self.rated_kva * 1000 / (math.sqrt(3) * self.rated_voltage_v)
        if current > 200000:
            raise ValueError('Derived rated current exceeds supported 200,000 A range.')
        return self

class AssetCreate(Input):
    asset_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(default='', max_length=200)
    timezone: str = 'UTC'
    configuration: Configuration = Field(default_factory=Configuration)

class Measurements(Input):
    voltage_r_v: float | None = Field(default=None, ge=0, le=1000000)
    voltage_y_v: float | None = Field(default=None, ge=0, le=1000000)
    voltage_b_v: float | None = Field(default=None, ge=0, le=1000000)
    current_r_a: float | None = Field(default=None, ge=0, le=1000000)
    current_y_a: float | None = Field(default=None, ge=0, le=1000000)
    current_b_a: float | None = Field(default=None, ge=0, le=1000000)
    oil_temperature_c: float | None = Field(default=None, ge=-60, le=250)
    ambient_temperature_c: float | None = Field(default=None, ge=-60, le=100)
    oil_level_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator('*', mode='before')
    @classmethod
    def no_boolean_measurements(cls, value):
        if isinstance(value, bool):
            raise ValueError('Boolean values are not measurements.')
        return value

    @model_validator(mode='after')
    def some_data(self):
        if all(getattr(self, channel) is None for channel in CHANNELS):
            raise ValueError('At least one measurement is required.')
        return self

class DeviceReading(Input):
    message_id: str = Field(min_length=1, max_length=120)
    timestamp: datetime
    measurements: Measurements

    @model_validator(mode='after')
    def aware(self):
        if self.timestamp.tzinfo is None:
            raise ValueError('Device timestamps must include a timezone offset.')
        return self

class RunCreate(Input):
    asset_id: str
    scenario: SCENARIOS = 'normal'
    seed: int = Field(default=42, ge=0, le=2147483647)
    interval_seconds: float = Field(default=2, ge=.5, le=60)

class RunUpdate(Input):
    scenario: SCENARIOS | None = None
    status: Literal['running', 'stopped'] | None = None
