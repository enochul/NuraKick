from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
import threading
import csv
import datetime
import sys

# We will just test the Arm to keep it simple
mac = "C6:0D:15:58:CE:83"
callbacks = []

print("=== NuraKick Monolith Sanity Check ===")
print(f"Connecting to {mac}...")

try:
    device = MetaWear(mac)
    device.connect()
    print("  -> Connected successfully.")
except Exception as e:
    print(f"  -> Failed to connect: {e}")
    sys.exit(1)

try:
    # 1. Wipe everything to guarantee a clean slate
    libmetawear.mbl_mw_metawearboard_tear_down(device.board)
    sleep(1.0)
    
    # 2. Configure Sensor Fusion (IMU_PLUS)
    print("--- Configuring Sensor ---")
    libmetawear.mbl_mw_sensor_fusion_set_mode(device.board, SensorFusionMode.IMU_PLUS)
    libmetawear.mbl_mw_sensor_fusion_set_acc_range(device.board, SensorFusionAccRange._8G)
    libmetawear.mbl_mw_sensor_fusion_set_gyro_range(device.board, SensorFusionGyroRange._2000DPS)
    libmetawear.mbl_mw_sensor_fusion_write_config(device.board)
    
    signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(device.board, SensorFusionData.QUATERNION)

    # 3. Setup Python Data Handler
    dataset = []
    def data_handler(context, data):
        try:
            quat = parse_value(data)
            dataset.append({
                "epoch_ms": data.contents.epoch,
                "w": quat.w, "x": quat.x, "y": quat.y, "z": quat.z
            })
        except Exception as e:
            # COMPLETELY UNMASKED. If it fails, we will see exactly why.
            print(f"\n[PARSER ERROR]: {e}")

    data_cb = FnVoid_VoidP_DataP(data_handler)
    callbacks.append(data_cb)

    # 4. Attach Logger
    logger_event = threading.Event()
    def logger_handler(context, logger):
        if logger:
            libmetawear.mbl_mw_logger_subscribe(logger, None, data_cb)
            print("  -> Internal logger successfully hooked.")
        else:
            print("  -> ERROR: Failed to create internal logger.")
        logger_event.set()

    log_cb = FnVoid_VoidP_VoidP(logger_handler)
    callbacks.append(log_cb)
    
    libmetawear.mbl_mw_datasignal_log(signal, None, log_cb)
    logger_event.wait(timeout=5.0)

    # 5. Start Hardware
    libmetawear.mbl_mw_logging_start(device.board, 0)
    libmetawear.mbl_mw_sensor_fusion_enable_data(device.board, SensorFusionData.QUATERNION)
    libmetawear.mbl_mw_sensor_fusion_start(device.board)
    
    # Power on the physical IMU so the algorithm has raw data to chew on
    libmetawear.mbl_mw_acc_start(device.board)
    libmetawear.mbl_mw_gyro_bmi160_start(device.board)

    # 6. The 10-Second Test Window
    print("\n=== SENSOR IS LIVE ===")
    print("SHAKE THE SENSOR CONTINUOUSLY FOR 10 SECONDS!")
    for i in range(30, 0, -1):
        print(f"  {i}...")
        sleep(1.0)

    # 7. Stop Hardware
    print("\n--- Stopping and Extracting ---")
    libmetawear.mbl_mw_acc_stop(device.board)
    libmetawear.mbl_mw_gyro_bmi160_stop(device.board)
    libmetawear.mbl_mw_sensor_fusion_stop(device.board)
    libmetawear.mbl_mw_logging_stop(device.board)
    libmetawear.mbl_mw_logging_flush_page(device.board)
    sleep(1.0)

    # 8. Download Flash Memory
    download_done = threading.Event()
    def progress_handler(context, entries_left, total_entries):
        if entries_left == 0:
            download_done.set()
    
    prog_cb = FnVoid_VoidP_UInt_UInt(progress_handler)
    callbacks.append(prog_cb)
    
    dl_handler = LogDownloadHandler(context=None, 
                                    received_progress_update=prog_cb, 
                                    received_unknown_entry=cast(None, FnVoid_VoidP_UByte_Long_UByteP_UByte), 
                                    received_unhandled_entry=cast(None, FnVoid_VoidP_DataP))

    libmetawear.mbl_mw_logging_download(device.board, 100, byref(dl_handler))
    download_done.wait(timeout=15.0)

    # 9. Save Data
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"NuraKick_SanityCheck_{timestamp}.csv"
    
    print(f"\n  -> Total valid Quaternion rows parsed: {len(dataset)}")
    if len(dataset) > 0:
        with open(filename, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=["epoch_ms", "w", "x", "y", "z"])
            writer.writeheader()
            writer.writerows(dataset)
        print(f"  -> File saved successfully to {filename}.")
    else:
        print("  -> FAILURE: No data parsed.")

except Exception as e:
    print(f"\nCRITICAL SCRIPT ERROR: {e}")

finally:
    print("\nCleaning up...")
    try:
        libmetawear.mbl_mw_metawearboard_tear_down(device.board)
        device.disconnect()
        print("  -> Disconnected safely.")
    except Exception:
        pass