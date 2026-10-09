"""Registry API fields use explicit units; unknown thermal values stay absent."""

from datetime import timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


def normalize_utc(value):
    try:
        return value.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise ValueError("timestamp cannot be represented in UTC") from None


UTCDateTime = Annotated[AwareDatetime, AfterValidator(normalize_utc)]
PositiveFinite = Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]
Finite = Annotated[float, Field(allow_inf_nan=False, strict=True)]
Source = Literal["assumed", "simulated", "nameplate", "measured"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, from_attributes=True
    )


class AssetCreate(StrictSchema):
    asset_id: str = Field(
        min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )
    name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=500)
    timezone: str = Field(min_length=1, max_length=100)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a valid IANA timezone") from None
        return value


class OperationalLimits(StrictSchema):
    max_load_pct: PositiveFinite | None = None
    min_voltage_pu: PositiveFinite | None = None
    max_voltage_pu: PositiveFinite | None = None
    max_top_oil_temp_c: Finite | None = Field(default=None, gt=-273.15)
    max_hot_spot_temp_c: Finite | None = Field(default=None, gt=-273.15)

    @model_validator(mode="after")
    def ordered_limits(self):
        if (
            self.min_voltage_pu is not None
            and self.max_voltage_pu is not None
            and self.min_voltage_pu >= self.max_voltage_pu
        ):
            raise ValueError("min_voltage_pu must be less than max_voltage_pu")
        if (
            self.max_top_oil_temp_c is not None
            and self.max_hot_spot_temp_c is not None
            and self.max_top_oil_temp_c > self.max_hot_spot_temp_c
        ):
            raise ValueError("max_top_oil_temp_c must not exceed max_hot_spot_temp_c")
        return self


class ThermalParameters(StrictSchema):
    rated_top_oil_rise_c: PositiveFinite | None = None
    rated_hot_spot_rise_c: PositiveFinite | None = None
    oil_time_constant_min: PositiveFinite | None = None
    winding_time_constant_min: PositiveFinite | None = None
    loss_ratio: PositiveFinite | None = None
    oil_exponent: PositiveFinite | None = None
    winding_exponent: PositiveFinite | None = None


class ConfigurationCreate(StrictSchema):
    rated_kva: PositiveFinite = Field(
        description="Total three-phase apparent-power rating in kVA"
    )
    rated_voltage_v: PositiveFinite = Field(
        description="RMS volts on measurement_side, using voltage_convention"
    )
    rated_current_a: PositiveFinite = Field(
        description="RMS line current in amperes on measurement_side"
    )
    voltage_convention: Literal["phase_to_neutral", "line_to_line"]
    measurement_side: Literal["primary", "secondary"]
    cooling_type: str = Field(
        min_length=1, max_length=50, description="Nameplate cooling class, e.g. ONAN"
    )
    operational_limits: OperationalLimits = Field(default_factory=OperationalLimits)
    thermal_parameters: ThermalParameters = Field(default_factory=ThermalParameters)
    parameter_provenance: dict[str, Source] = Field(
        description="Source for every supplied parameter; nested keys use dotted paths"
    )

    @model_validator(mode="after")
    def complete_provenance(self):
        required = {
            "rated_kva",
            "rated_voltage_v",
            "rated_current_a",
            "voltage_convention",
            "measurement_side",
            "cooling_type",
        }
        for group in ("operational_limits", "thermal_parameters"):
            required.update(
                f"{group}.{key}"
                for key in getattr(self, group).model_dump(exclude_none=True)
            )
        if set(self.parameter_provenance) != required:
            raise ValueError(
                "parameter_provenance must contain exactly the supplied parameter paths: "
                + ", ".join(sorted(required))
            )
        return self


class ConfigurationResponse(ConfigurationCreate):
    asset_id: str
    version: int = Field(gt=0)
    created_at: UTCDateTime


class AssetResponse(AssetCreate):
    created_at: UTCDateTime
    current_configuration: ConfigurationResponse | None = None


class AssetPage(StrictSchema):
    items: list[AssetResponse]
    limit: int
    offset: int


class ConfigurationPage(StrictSchema):
    items: list[ConfigurationResponse]
    limit: int
    offset: int
