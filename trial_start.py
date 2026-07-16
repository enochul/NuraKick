import pandas as pd
import numpy as np
from enum import Enum

# ==========================================
# 1. GLOBAL CONFIGURATIONS & CONSTANTS
# ==========================================

# Hardware & Data Chunking
SAMPLE_RATE_HZ = 50
CHUNK_DURATION_SEC = 10
CHUNK_SIZE = SAMPLE_RATE_HZ * CHUNK_DURATION_SEC

# State Machine Thresholds (To be tuned with clinical data)
VM_SLEEP_THRESHOLD = 1.05
SYNC_HELD_THRESHOLD = 0.85
PITCH_PRONE_THRESHOLD = -45.0  # Degrees indicating face-down

# ==========================================
# 2. STATE MACHINE ENUMS & VARIABLES
# ==========================================

class InfantState(Enum):
    SLEEP = "SLEEP"
    HELD_RHYTHMIC = "HELD_RHYTHMIC"
    PRONE_TUMMY = "PRONE_TUMMY"
    SIDE_LEFT = "SIDE_LEFT"
    SIDE_RIGHT = "SIDE_RIGHT"
    SUPINE_PLAY = "SUPINE_PLAY" # The Goldilocks Zone

# Global Tracking Variables
current_state = InfantState.SLEEP
actionable_chunks_saved = 0

# ==========================================
# 3. SIGNAL PROCESSING & MATH (STUBS)
# ==========================================

def apply_butterworth_filter(data_chunk):
    """
    TODO: Implement a 4th-order low-pass Butterworth filter.
    Goal: Remove electrical static/noise above 20Hz.
    """
    clean_chunk = data_chunk # Placeholder
    return clean_chunk

def calculate_vector_magnitude(data_chunk):
    """
    TODO: Calculate VM for Ankle_L, Ankle_R, and Trunk sensors independently.
    """
    # Placeholder: Returning a dictionary of dummy average VMs
    return {"ankle_L": 1.0, "ankle_R": 1.0, "trunk": 1.0}

def check_limb_synchronization(trunk_vm, ankle_vm):
    """
    TODO: Run cross-correlation between trunk and ankles. 
    Goal: Detect external rocking or carrying by parents.
    """
    return False # Placeholder: Assume limbs are moving independently

def calculate_trunk_pitch(trunk_data):
    """
    TODO: Use sensor fusion to determine absolute Z-axis orientation.
    Goal: Identify if the baby is face-down (Tummy Time).
    """
    return 0.0 # Placeholder: 0.0 = flat on back

# ==========================================
# 4. THE FINITE STATE MACHINE (FSM) LOGIC
# ==========================================

def evaluate_fsm_transitions(vms, sync_flag, trunk_pitch):
    """
    Routes the current chunk of data into the correct behavioral bucket.
    """
    global current_state
    
    # Gate 1: Is the overall movement basically zero? (Gravity only)
    if vms["trunk"] <= VM_SLEEP_THRESHOLD and vms["ankle_L"] <= VM_SLEEP_THRESHOLD:
        current_state = InfantState.SLEEP
        return current_state
        
    # Gate 2: Is the baby face down?
    if trunk_pitch < PITCH_PRONE_THRESHOLD:
        current_state = InfantState.PRONE_TUMMY
        return current_state
        
    # Gate 3: Are the limbs moving in perfect rhythm with the chest?
    if sync_flag == True:
        current_state = InfantState.HELD_RHYTHMIC
        return current_state
        
    # If awake, on back, and moving autonomously -> Target Data
    current_state = InfantState.SUPINE_PLAY
    return current_state

# ==========================================
# 5. MAIN EXECUTION PIPELINE
# ==========================================

def main():
    global actionable_chunks_saved
    
    print("--- Initializing NuraKick Data Pipeline ---")
    filepath = "incoming_sensor_data/session_001_mbient.csv"
    
    try:
        # Stream the massive file in memory-safe chunks
        for chunk_index, data_chunk in enumerate(pd.read_csv(filepath, chunksize=CHUNK_SIZE)):
            
            # Step 1: Clean the raw data
            clean_chunk = apply_butterworth_filter(data_chunk)
            
            # Step 2: Extract specific physiological features
            vms = calculate_vector_magnitude(clean_chunk)
            sync_flag = check_limb_synchronization(vms["trunk"], vms["ankle_L"])
            trunk_pitch = calculate_trunk_pitch(clean_chunk)
            
            # Step 3: Route through the State Machine
            active_state = evaluate_fsm_transitions(vms, sync_flag, trunk_pitch)
            
            # Step 4: Action Phase
            if active_state == InfantState.SUPINE_PLAY:
                # TODO: Append clean_chunk to finished_data.csv and run Entropy math
                actionable_chunks_saved += 1
                print(f"[{chunk_index * 10}s] SUPINE PLAY detected. Actionable data saved.")
            else:
                # Discard noise chunk (Sleep, Held, Tummy Time)
                pass
                
    except FileNotFoundError:
        print(f"Error: Could not locate {filepath}. Waiting for sensor data...")

    print(f"\n--- Pipeline Complete ---")
    print(f"Total actionable chunks saved for Entropy Analysis: {actionable_chunks_saved}")

if __name__ == "__main__":
    main()