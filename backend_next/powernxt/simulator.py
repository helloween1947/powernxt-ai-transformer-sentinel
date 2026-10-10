"""Deterministic synthetic readings with coupled loading/thermal evolution."""
import math
import random
from .schemas import CHANNELS

def generate(config, scenario, seed, step, interval, previous=None):
    rng = random.Random(seed + step)
    load = max(1.5, config['operational_limits']['max_load_pct']/100 + .2) if scenario == 'overload' else .65 + .08 * math.sin(step/18)
    ambient = 28 + 2 * math.sin(step/80)
    currents = [config['rated_current_a'] * load * (1 + rng.uniform(-.01, .01)) for _ in range(3)]
    volts = [config['rated_voltage_v'] * (1 + rng.uniform(-.01, .01)) for _ in range(3)]
    if scenario == 'phase_imbalance':
        currents[0] *= 1.5
        currents[2] *= .7
    if scenario == 'undervoltage':
        volts[0] *= .8
    target = ambient + config['rated_top_oil_rise_c'] * load**1.6
    prior_oil = previous['oil_temperature_c'] if previous and previous['oil_temperature_c'] is not None else target
    oil = prior_oil + (target-prior_oil) * -math.expm1(-interval/config['oil_time_constant_s'])
    if scenario == 'overheating':
        oil = max(oil, config['operational_limits']['max_top_oil_temp_c'] + 8)
    values = dict(zip(CHANNELS[:6], [*volts, *currents]))
    values.update(oil_temperature_c=round(oil, 3), ambient_temperature_c=round(ambient, 3),
                  oil_level_pct=max(0, min(45, config['operational_limits']['min_oil_level_pct']-5) + rng.uniform(-1, 1)) if scenario == 'low_oil' else 82 + rng.uniform(-.3, .3))
    return values
