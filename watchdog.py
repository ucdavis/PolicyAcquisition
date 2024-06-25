import subprocess
import time

command = ["python", "background/update.py"]

# Just run the update script in a loop, restarting if it fails

while True:
    try:
        print(f"Starting process: {' '.join(command)}")
        process = subprocess.Popen(command)
        process.wait()
    except Exception as e:
        print(f"Process failed with error: {e}")
    print("Restarting process in 5 seconds...")
    time.sleep(5)
