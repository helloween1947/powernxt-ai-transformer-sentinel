"""Person B explicit thermal-core constructor; no parameter defaults."""
import math
from .core import AssetConfig

def _thermal_core(config):
    """Construct the shared core with explicit coefficients; no parameter fallback."""
    params = config["thermal_parameters"]
    return AssetConfig(asset_id=config["asset_id"], rated_current_a=config["rated_current_a"],
                       rated_phase_voltage_v=config["rated_voltage_v"] / (math.sqrt(3) if config["voltage_convention"] == "line_to_line" else 1),
                       rated_oil_rise_c=params["rated_top_oil_rise_c"], time_constant_s=params["oil_time_constant_min"] * 60,
                       loss_ratio=params["loss_ratio"], oil_exponent=params["oil_exponent"])
