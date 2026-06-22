from safety_gateway import MLScout
import numpy as np

scout = MLScout()
test_data = {
    'speed_kmh': 100.0,
    'engine_temp_c': 90.0,
    'tire_pressure_psi': 32.0,
    'throttle_pct': 100.0,
    'engine_load_pct': 10.0,
    'maf_g_sec': 30.0,
    'engine_rpm': 2500.0,
    'oil_pressure_psi': 40.0,
    'battery_voltage_v': 13.5,
    'fuel_level_pct': 85.0,
    'tire_pressure_fl_psi': 32.0,
    'tire_pressure_fr_psi': 32.0,
    'tire_pressure_rl_psi': 32.0,
    'tire_pressure_rr_psi': 32.0,
}
pred, score = scout.evaluate(test_data)
print(f'Pred (throttle=100, load=10): {pred}, Score: {score}')
