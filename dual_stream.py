# This file uses the on-board Sensor fusion to visually show the orientation of ONE sensor.
# Streams the Sensor Fusion data live, so only one sensor is used here for a clean bandwidth.

from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
from vpython import box, vector, rate, color, canvas, label, cylinder, compound

# --- CONFIGURATION ---
MAC_ADDRESS = "C6:0D:15:58:CE:83"  # Arm Sensor

# --- 3D SCENE SETUP (VPython) ---
scene = canvas(title='NuraKick Live Sensor Fusion', width=800, height=600, background=color.gray(0.1))

# --- CREATE CUSTOM SENSOR MODEL ---
# 1. Define the main body. 
# Swapped dimensions: X-axis (length) is now the short side, Z-axis (width) is the long side.
body_length = 3.0  # Short side (X-axis)
body_width = 4.0   # Long side (Z-axis)
body_height = 0.8  # Thickness (Y-axis)
main_body = box(length=body_length, width=body_width, height=body_height, color=color.white)

# 2. Define the gray button for reference
# Placed in the positive X (right) and positive Z (bottom/front) corner.
button_radius = 0.4
button_height = 0.1 

button_x = (body_length / 2) - 0.6  # Shifted to the right edge
button_y = (body_height / 2)        # Sitting on top of the surface
button_z = (body_width / 2) - 0.6   # Shifted to the bottom/front edge

sensor_button = cylinder(pos=vector(button_x, button_y, button_z),
                         axis=vector(0, button_height, 0), 
                         radius=button_radius,
                         color=color.gray(0.5))

# 3. Combine them into a single compound object.
sensor_model = compound([main_body, sensor_button])

# Global dictionary to hold the latest angles from Bluetooth
current_angles = {"pitch": 0.0, "roll": 0.0, "yaw": 0.0}

def sensor_fusion_handler(context, data):
    """ Callback to catch the 100Hz Euler Angles from the Bosch Chip """
    euler = parse_value(data)
    current_angles["pitch"] = euler.pitch
    current_angles["roll"] = euler.roll
    current_angles["yaw"] = euler.heading

callback = FnVoid_VoidP_DataP(sensor_fusion_handler)

# --- HARDWARE CONNECTION ---
print("Connecting to sensor...")
device = MetaWear(MAC_ADDRESS)
device.connect()
print("Connected! Waking up Bosch Sensor Fusion...")

try:
    libmetawear.mbl_mw_sensor_fusion_set_mode(device.board, SensorFusionMode.NDOF)
    libmetawear.mbl_mw_sensor_fusion_write_config(device.board)

    signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(device.board, SensorFusionData.EULER_ANGLE)
    libmetawear.mbl_mw_datasignal_subscribe(signal, None, callback)

    libmetawear.mbl_mw_sensor_fusion_enable_data(device.board, SensorFusionData.EULER_ANGLE)
    libmetawear.mbl_mw_sensor_fusion_start(device.board)

    print("\n--- 3D RENDER ACTIVE ---")
    print("Look at the browser window that just opened!")
    print("Press Ctrl+C in this terminal to stop.")

    while True:
        rate(100) 
        
        from math import radians, sin, cos
        
        p = radians(current_angles["pitch"])
        r = radians(current_angles["roll"])
        y = radians(current_angles["yaw"])
        
        sensor_model.axis = vector(cos(p)*cos(y), sin(p)*cos(y), -sin(y))
        sensor_model.up = vector(-sin(r)*sin(y)*cos(p) - cos(r)*sin(p), 
                                cos(r)*cos(p) - sin(r)*sin(y)*sin(p), 
                                -sin(r)*cos(y))

except KeyboardInterrupt:
    print("\nStopping 3D stream...")

finally:
    libmetawear.mbl_mw_sensor_fusion_stop(device.board)
    libmetawear.mbl_mw_sensor_fusion_clear_enabled_mask(device.board)
    libmetawear.mbl_mw_datasignal_unsubscribe(signal)
    libmetawear.mbl_mw_debug_reset(device.board)
    sleep(2.0)
    print("Hardware disconnected safely.")