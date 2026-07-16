from mbientlab.metawear import MetaWear, libmetawear
from time import sleep

SENSORS = {
    #"Leg": "C1:6F:3F:C1:2F:1A",
    "Arm": "C6:0D:15:58:CE:83"
}

print("=== NuraKick Hardware Factory Reset ===")

for name, mac in SENSORS.items():
    print(f"\nConnecting to {name} ({mac})...")
    try:
        device = MetaWear(mac)
        device.connect()
        
        # 1. Tear down all internal routing tables and ghost loggers
        libmetawear.mbl_mw_metawearboard_tear_down(device.board)
        
        # 2. Issue a hard hardware reboot (This instantly drops the BLE connection)
        libmetawear.mbl_mw_debug_reset(device.board)
        
        # We do NOT call device.disconnect() because the reset already severed the tether.
        sleep(1.5) 
        
        print(f"  -> {name} routing tables cleared. Board is rebooting.")
    except Exception as e:
        print(f"  -> ERROR resetting {name}: {e}")

print("\n=== RESET COMPLETE ===")