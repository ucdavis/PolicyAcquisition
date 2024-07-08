import subprocess
import time

from background.logger import setup_logger

logger = setup_logger()

command = ["python", "background/update.py"]

# Just run the update script in a loop, restarting if it fails

while True:
    try:
        logger.info(f"Starting process: {' '.join(command)}")
        process = subprocess.Popen(command)
        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
    except subprocess.CalledProcessError as e:
        logger.exception(f"Process failed with a non-zero exit code: {e.returncode}")
    except Exception as e:
        logger.exception(f"Process failed with error: {e}")

    logger.info("Restarting process in 5 seconds...")
    time.sleep(5)
