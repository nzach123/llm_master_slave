import psutil
import subprocess
import logging
import time

logger = logging.getLogger(__name__)

def get_available_ram():
    """Get available system RAM in GB."""
    return psutil.virtual_memory().available / (1024 ** 3)

def get_available_vram():
    """
    Get available VRAM in GB using nvidia-smi.
    Returns 100.0 if nvidia-smi is not found (assuming no GPU limit).
    """
    try:
        # Run nvidia-smi to get free memory in MiB
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,nounits,noheader"],
            encoding='utf-8',
            stderr=subprocess.DEVNULL
        )
        # Sum free memory from all GPUs
        free_mibs = sum(int(line.strip()) for line in output.strip().split('\n') if line.strip())
        return free_mibs / 1024.0
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        # nvidia-smi not available or failed
        return 100.0

def check_resources_threshold(min_gb=2.0):
    """
    Verify if system resources meet the minimum threshold.
    Returns True if both RAM and VRAM (where applicable) are above min_gb.
    """
    ram = get_available_ram()
    vram = get_available_vram()
    
    if ram < min_gb:
        logger.warning(f"System RAM below threshold: {ram:.2f}GB < {min_gb}GB")
        return False
    
    if vram < min_gb:
        logger.warning(f"VRAM below threshold: {vram:.2f}GB < {min_gb}GB")
        return False
        
    return True

def wait_for_resources(min_gb=2.0, timeout_seconds=600, check_interval=30):
    """
    Wait for resources to become available.

    Args:
        min_gb: Minimum GB required for RAM and VRAM.
        timeout_seconds: Maximum time to wait in seconds (default: 10 mins).
        check_interval: Time to sleep between checks (default: 30s).

    Returns:
        True if resources became available, False if timeout reached.
    """
    start_time = time.time()

    if check_resources_threshold(min_gb):
        return True

    logger.info(f"Resources low (<{min_gb}GB). Entering wait loop (timeout={timeout_seconds}s)...")

    while time.time() - start_time < timeout_seconds:
        time.sleep(check_interval)
        if check_resources_threshold(min_gb):
            logger.info("Resources recovered.")
            return True

        logger.info(f"Still waiting for resources... ({int(time.time() - start_time)}s elapsed)")

    logger.error(f"Resource wait timed out after {timeout_seconds}s")
    return False
