"""Generic runtime detection using registry metadata."""

import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .registry import SUPPORTED_RUNTIMES
from ..utils.logging import get_logger

logger = get_logger("runtime.detector")


def detect_runtime(runtime_name: str) -> Dict[str, Any]:
    """
    Detect runtime using registry metadata.
    
    Args:
        runtime_name: Name of runtime to detect (e.g., "ollama")
        
    Returns:
        Standardized detection result:
        {
            "runtime": str,
            "available": bool,
            "binary_found": bool,
            "service_reachable": bool,
            "version": str
        }
    """
    if runtime_name not in SUPPORTED_RUNTIMES:
        return {
            "runtime": runtime_name,
            "available": False,
            "binary_found": False,
            "service_reachable": False,
            "version": None
        }
    
    registry = SUPPORTED_RUNTIMES[runtime_name]
    binary = registry["binary"]
    api_base = registry["api_base"]
    
    # Check binary exists
    binary_found = False
    version = None
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            binary_found = True
            version = result.stdout.strip().split()[0] if result.stdout.strip() else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Check service available
    service_reachable = False
    try:
        url = f"{api_base}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                service_reachable = True
    except (urllib.error.URLError, Exception):
        pass
    
    available = binary_found and service_reachable
    
    return {
        "runtime": runtime_name,
        "available": available,
        "binary_found": binary_found,
        "service_reachable": service_reachable,
        "version": version
    }

