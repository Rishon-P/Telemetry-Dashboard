import json
import random

def calculate_comprehensive_physics():
    # 1. Generate Golden Baseline (Healthy) Parameters
    speed = random.randint(20, 250)
    rpm = random.randint(1500, 6000)
    gear = random.randint(2, 6)
    load = random.randint(20, 80)
    
    engine_temp = random.randint(85, 105) # Normal Temp
    oil_pressure = random.randint(40, 80) # Normal Oil
    fuel_level = random.randint(15, 100)  # Normal Fuel
    voltage = round(random.uniform(13.5, 14.5), 1) # Normal Alternator Output
    
    # Mathematical baselines
    expected_tire_psi = round(32.0 + (speed / 38.0), 1)
    base_rpm = speed * (gear * 0.8) * 10
    expected_maf = round((rpm * load * 2.0 * 1.225) / 12000.0, 1)
    
    tire_fl = expected_tire_psi + round(random.uniform(-0.5, 0.5), 1)
    tire_fr = expected_tire_psi + round(random.uniform(-0.5, 0.5), 1)
    tire_rl = expected_tire_psi + round(random.uniform(-0.5, 0.5), 1)
    tire_rr = expected_tire_psi + round(random.uniform(-0.5, 0.5), 1)
    maf = expected_maf

    # 2. Select the specific Anomaly State (10 possible states)
    scenarios = [
        "healthy", "tire_thermal_dev", "transmission_dev", "airflow_dev", "electrical_dev",
        "engine_overheat", "oil_starvation", "maf_dead", "critical_fuel", "tire_blowout"
    ]
    # Weigh it so 20% is healthy, 80% is anomalies
    scenario = random.choices(scenarios, weights=[20, 9, 9, 9, 9, 9, 9, 9, 8, 9], k=1)[0]
    
    root_cause = "System Normal"
    diagnostic_output = "All 14 telemetry parameters fall within expected mathematical boundaries. No anomalies detected."

    # 3. Inject the Anomaly
    if scenario == "engine_overheat":
        root_cause = "Engine Overheating"
        engine_temp = random.randint(116, 150)
        diagnostic_output = f"Engine temperature has reached a critical {engine_temp}°C, exceeding the safe threshold. Immediate shutdown required to prevent catastrophic block warp or head gasket failure."
        
    elif scenario == "oil_starvation":
        root_cause = "Oil Starvation"
        oil_pressure = random.randint(0, 19)
        diagnostic_output = f"At {rpm} RPM, oil pressure has plummeted to {oil_pressure} PSI. This indicates severe oil starvation; engine components lack lubrication, risking immediate metal-on-metal destruction."

    elif scenario == "critical_fuel":
        root_cause = "Critical Fuel Level"
        fuel_level = random.randint(0, 4)
        diagnostic_output = f"Fuel level has dropped to {fuel_level}%. The vehicle is at immediate risk of stalling due to fuel starvation."

    elif scenario == "maf_dead":
        root_cause = "MAF Sensor Dead"
        maf = round(random.uniform(0.0, 9.9), 1)
        diagnostic_output = f"Engine is operating at {rpm} RPM, but the Mass Air Flow sensor is reporting only {maf} g/s. This indicates a dead sensor or a completely suffocated intake."

    elif scenario == "tire_blowout":
        root_cause = "Tire Pressure Critical"
        # Pick one random tire to blow out
        blown_tire = random.choice(["FL", "FR", "RL", "RR"])
        bad_pressure = random.randint(0, 14)
        if blown_tire == "FL": tire_fl = bad_pressure
        if blown_tire == "FR": tire_fr = bad_pressure
        if blown_tire == "RL": tire_rl = bad_pressure
        if blown_tire == "RR": tire_rr = bad_pressure
        diagnostic_output = f"Tire {blown_tire} has suffered a catastrophic loss of pressure, currently reading {bad_pressure} PSI. Immediate halt required to prevent loss of vehicle control."

    elif scenario == "tire_thermal_dev":
        root_cause = "Tire Thermal Deviation"
        offset = random.uniform(-15.0, -5.0) if random.choice([True, False]) else random.uniform(10.0, 20.0)
        tire_fl = round(expected_tire_psi + offset, 1)
        tire_fr = round(expected_tire_psi + offset, 1)
        tire_rl = round(expected_tire_psi + offset, 1)
        tire_rr = round(expected_tire_psi + offset, 1)
        avg_psi = round((tire_fl + tire_fr + tire_rl + tire_rr) / 4, 1)
        direction = "under-pressurized/too cold" if offset < 0 else "over-pressurized/overheating"
        diagnostic_output = f"At {speed} km/h, the average tire pressure is {avg_psi} PSI (expected {expected_tire_psi} PSI). The tires are mathematically {direction} and misaligned with expected high-speed thermal expansion."

    elif scenario == "transmission_dev":
        root_cause = "Transmission Deviation"
        rpm = int(base_rpm + random.randint(1500, 3500))
        diagnostic_output = f"At {speed} km/h in gear {gear}, engine is spinning at {rpm} RPM. This heavily exceeds the expected kinematic ratio, indicating severe drivetrain slip or mechanical disconnect."

    elif scenario == "airflow_dev":
        root_cause = "Airflow Deviation"
        maf = round(expected_maf - random.uniform(30.0, 70.0), 1)
        if maf < 10: maf = 12.0 # Keep it out of Layer 1 territory
        diagnostic_output = f"At {rpm} RPM and {load}% load, expected mass air flow is {expected_maf} g/s, but actual reading is {maf} g/s. The engine is missing critical airflow, indicating a severe intake restriction."

    elif scenario == "electrical_dev":
        root_cause = "Electrical Deviation"
        voltage = round(random.uniform(9.0, 11.5), 1)
        diagnostic_output = f"At {rpm} RPM, expected alternator output is ~13.8V. Current system voltage is severely depleted at {voltage}V, indicating alternator failure or severe parasitic draw."

    # 4. Format the final string exactly as the Python backend will send it
    input_str = (f"Speed:{speed}km/h | RPM:{rpm} | Gear:{gear} | Load:{load}% | "
                 f"Temp:{engine_temp}C | Oil:{oil_pressure}PSI | Fuel:{fuel_level}% | Volt:{voltage}V | "
                 f"MAF:{maf}g/s | Tires(FL,FR,RL,RR):[{tire_fl}, {tire_fr}, {tire_rl}, {tire_rr}]PSI | "
                 f"Root Cause Flag:{root_cause}")
    
    return {
        "instruction": "You are a highly precise automotive ECU diagnostic AI. Analyze the comprehensive raw telemetry and state the exact mechanical conclusion.",
        "input": input_str,
        "output": diagnostic_output
    }

print("Generating 2,000-row Comprehensive Telemetry Dataset...")
dataset = [calculate_comprehensive_physics() for _ in range(2000)]

with open("telemetry_training_data.jsonl", "w") as f:
    for item in dataset:
        f.write(json.dumps(item) + "\n")
        
print("Complete. 'telemetry_training_data.jsonl' is fully prepared for Colab upload.")