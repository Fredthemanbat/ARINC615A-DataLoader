import os
import psutil
import time
from datetime import datetime

ROOT=""

desktop = os.path.join(os.path.expanduser("~"), "Desktop")

def check_ethernet(interface='enp43s0'):
    for iface, addrs in psutil.net_if_stats().items():
        if iface == interface:
            return addrs.isup 
    return False

def create_file_on_desktop():
    filename = f"Ethernet_Connection_Status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_path = f'{ROOT}{filename}'
    with open(file_path, 'w') as f:
        f.write("No Ethernet connection detected.")
    print(f"File created: {file_path}")

def create_folder():
    dirname = f"Ethernet_Connection_Status_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    newpath =f'{ROOT}{dirname}'
    if not os.path.exists(newpath):
        os.makedirs(newpath)

def monitor_ethernet():
    was_ethernet_up = check_ethernet()

    while True:
        print("Checking again")
        is_ethernet_up = check_ethernet()

        if is_ethernet_up and not was_ethernet_up:
            print("Ethernet plugged in. Stopping file creation.")
            break

        elif was_ethernet_up and is_ethernet_up:
            print("Ethernet plugged in")
            break

        elif not is_ethernet_up and was_ethernet_up:
            print("Ethernet unplugged. Starting file creation.")
            create_folder()
        
        elif not was_ethernet_up and not is_ethernet_up:
            print("Ethernet unplugged. Starting file creation.")
            create_folder()

        was_ethernet_up = is_ethernet_up
        
        time.sleep(5)

if __name__ == "__main__":
    monitor_ethernet()
