import psutil
import subprocess
import logging

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
        logger.error(f"System RAM below threshold: {ram:.2f}GB < {min_gb}GB")
        return False
    
    if vram < min_gb:
        logger.error(f"VRAM below threshold: {vram:.2f}GB < {min_gb}GB")
        return False
        
    return True
