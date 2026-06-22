import csv
import random
import numpy as np

# ==========================================
# CONFIGURATION & VEHICLE CONSTANTS
# ==========================================
NUM_ROWS = 100000
FILENAME = "data/vehicle_training_data.csv" # Ensures it saves into your data folder
FEATURE_NAMES = ['speed', 'rpm', 'throttle', 'engine_load', 'maf', 'engine_temp', 'oil_pressure', 'battery_voltage', 'fuel_level', 'tp_fl', 'tp_fr', 'tp_rl', 'tp_rr', 'airflow_deviation','transmission_deviation','tire_thermal_deviation','electrical_deviation']

# Physics Constants (2.0L Sedan)
DISPLACEMENT_L = 2.0
AIR_DENSITY_G_L = 1.225
AFR = 14.7
FUEL_DENSITY_G_L = 745.0
TANK_CAPACITY_L = 50.0

TIRE_RADIUS_M = 0.31
FINAL_DRIVE = 3.50
GEAR_RATIOS = {1: 2.97, 2: 2.07, 3: 1.43, 4: 1.00, 5: 0.84, 6: 0.56}

def get_gear(speed):
    """Automatic Transmission Logic based on speed (km/h)"""
    if speed < 15: return 1
    elif speed < 35: return 2
    elif speed < 60: return 3
    elif speed < 90: return 4
    elif speed < 120: return 5
    else: return 6

def calculate_rpm(speed, gear):
    """Kinematic formula linking wheel speed to engine crankshaft RPM"""
    if speed <= 0: return 800.0 # Idle RPM
    gear_ratio = GEAR_RATIOS[gear]
    # RPM = (Speed * Gear * Final_Drive * 60) / (2 * Pi * Radius * 3.6)
    rpm = (speed * gear_ratio * FINAL_DRIVE / TIRE_RADIUS_M) * 2.65258
    return max(800.0, rpm) # Torque converter prevents dropping below idle

def calculate_maf(rpm, load_pct):
    """Volumetric Efficiency formula for Mass Air Flow (g/s)"""
    volumetric_efficiency = load_pct / 100.0
    maf = (rpm * DISPLACEMENT_L * volumetric_efficiency * AIR_DENSITY_G_L) / 120.0
    return max(2.0, maf)

def calculate_fuel_burn(maf):
    """Calculates exact % of tank consumed in 1 second based on MAF"""
    fuel_g_s = maf / AFR
    fuel_l_s = fuel_g_s / FUEL_DENSITY_G_L
    pct_drop = (fuel_l_s / TANK_CAPACITY_L) * 100.0
    return pct_drop

# ==========================================
# HYBRID STATE MACHINE & PHYSICS ENGINE
# ==========================================
def generate_dataset():
    print(f"Generating {NUM_ROWS} rows of pure kinematic telemetry...")
    
    with open(FILENAME, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(FEATURE_NAMES)
        
        # Initial Physics State
        speed = 0.0
        engine_temp = 85.0
        fuel_level = 100.0
        
        state_timer = 0
        current_state = "IDLE"
        states = ["IDLE", "CITY_CRUISE", "HARD_ACCEL", "HIGHWAY", "COASTING"]
        
        for i in range(NUM_ROWS):
            # 1. STATE MANAGEMENT
            if state_timer <= 0:
                current_state = random.choices(
                    states, weights=[0.2, 0.4, 0.1, 0.2, 0.1], k=1
                )[0]
                state_timer = random.randint(30, 180) # Hold state for 30s to 3 mins
            state_timer -= 1
            
            # 2. DRIVER INTENT (Throttle & Target Speed)
            if current_state == "IDLE":
                target_speed = 0.0
                throttle = 0.0
            elif current_state == "CITY_CRUISE":
                target_speed = random.uniform(30, 60)
                throttle = random.uniform(10, 25)
            elif current_state == "HARD_ACCEL":
                target_speed = random.uniform(80, 130)
                throttle = random.uniform(70, 95)
            elif current_state == "HIGHWAY":
                target_speed = random.uniform(100, 130)
                throttle = random.uniform(20, 35)
            elif current_state == "COASTING":
                target_speed = 0.0
                throttle = 0.0

            # 3. KINEMATIC CHAIN REACTION
            # Acceleration Physics
            acceleration_factor = (throttle / 100.0) * 2.5
            if target_speed > speed:
                speed += acceleration_factor
            else:
                speed -= 1.2 # Coasting/braking friction
                
            speed = max(0.0, speed)
            
            # Gear & RPM Physics
            gear = get_gear(speed)
            base_rpm = calculate_rpm(speed, gear)
            # Add torque converter slip based on throttle
            rpm = base_rpm + (throttle * 5.0) 
            
            # Engine Load Physics (High throttle at low RPM = High Load)
            if throttle > 0:
                engine_load = min(100.0, (throttle * 1.5) - (rpm / 10000.0))
            else:
                engine_load = 15.0 # Parasitic idle load
                
            # Air & Fuel Physics
            maf = calculate_maf(rpm, engine_load)
            fuel_level = max(2.0, fuel_level - calculate_fuel_burn(maf))
            
            # Thermal & Mechanical Physics
            temp_target = 85.0 + (engine_load * 0.15)
            engine_temp = engine_temp + (temp_target - engine_temp) * 0.01
            oil_pressure = 25.0 + (rpm / 1000.0) * 8.0 
            battery_voltage = 13.8 if rpm > 400 else 12.6
            
            # Tire Physics (Friction heat expands pressure)
            tire_expansion = (speed / 100.0) * 1.2
            base_tire = 32.0 + tire_expansion

            # 4. ADD REAL-WORLD NOISE (Jitter)
            speed_out = speed + random.uniform(-0.2, 0.2)
            rpm_out = rpm + random.uniform(-15, 15)
            throttle_out = throttle + random.uniform(-1.0, 1.0)
            load_out = engine_load + random.uniform(-1.5, 1.5)
            maf_out = maf + random.uniform(-0.5, 0.5)
            temp_out = engine_temp + random.uniform(-0.5, 0.5)
            oil_out = oil_pressure + random.uniform(-1.0, 1.0)
            batt_out = battery_voltage + random.uniform(-0.1, 0.1)
            tires_out = [base_tire + random.uniform(-0.2, 0.2) for _ in range(4)]

            # 5. CLAMP ABSOLUTE BOUNDARIES
            speed_out = max(0.0, min(speed_out, 200.0))
            rpm_out = max(0.0, min(rpm_out, 7000.0))
            throttle_out = max(0.0, min(throttle_out, 100.0))
            load_out = max(0.0, min(load_out, 100.0))
            maf_out = max(2.0, min(maf_out, 200.0))

            # --- NEW: FEATURE ENGINEERING (RESIDUALS) ---
            safe_rpm = max(1.0, rpm_out)
            safe_load = max(1.0, load_out)
            
            # Calculate exactly what the MAF should be based on 2.0L physics
            expected_maf = (safe_rpm * safe_load * 2.0 * 1.225) / 12000.0
            
            # The 14th feature is the pure deviation
            airflow_deviation = abs(maf_out - expected_maf)

            # 2. Drivetrain Residual
            expected_gear = get_gear(speed_out)
            base_rpm = (speed_out * GEAR_RATIOS[expected_gear] * FINAL_DRIVE / TIRE_RADIUS_M) * 2.65258
            expected_rpm = max(800.0, base_rpm) + (throttle_out * 5.0)
            transmission_deviation = abs(rpm_out - expected_rpm)

            # --- PASTE THE NEW TIRE THERMAL MATH HERE ---
            # 3. Tire Thermal Residual
            expected_tp = 32.0 + (speed_out / 38.0)
            tire_thermal_deviation = max(
                abs(tires_out[0] - expected_tp), abs(tires_out[1] - expected_tp),
                abs(tires_out[2] - expected_tp), abs(tires_out[3] - expected_tp)
            )
            # --------------------------------------------
            
            # 4. Electrical Residual
            expected_voltage = 13.8 if rpm_out > 400.0 else 12.6
            electrical_deviation = abs(batt_out - expected_voltage)
            
            # 6. WRITE ROW (Updated to 17 features)
            row = [
                round(speed_out, 2), round(rpm_out, 2), round(throttle_out, 2), round(load_out, 2), 
                round(maf_out, 2), round(temp_out, 2), round(oil_out, 2), 
                round(batt_out, 2), round(fuel_level, 4), 
                round(tires_out[0], 2), round(tires_out[1], 2), round(tires_out[2], 2), round(tires_out[3], 2),
                round(airflow_deviation, 4),
                round(transmission_deviation, 4),
                round(tire_thermal_deviation, 4),
                round(electrical_deviation, 4) # <-- THE 17TH FEATURE
            ]
            writer.writerow(row)

    print(f"Success! {FILENAME} has been generated with pure kinematic data.")

if __name__ == "__main__":
    generate_dataset()