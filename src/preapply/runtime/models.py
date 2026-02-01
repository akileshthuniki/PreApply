"""Model management operations for AI runtimes."""

import json
import urllib.request
import urllib.error
import subprocess
from typing import List, Optional
from .registry import SUPPORTED_RUNTIMES
from ..utils.logging import get_logger

logger = get_logger("runtime.models")


def list_available_models(runtime_name: str = "ollama") -> List[str]:
    """
    List models available in runtime (read-only).
    
    Args:
        runtime_name: Runtime to query (default: "ollama")
        
    Returns:
        List of available model names
        
    Raises:
        Exception: If runtime is not available or query fails
    """
    if runtime_name not in SUPPORTED_RUNTIMES:
        raise Exception(f"Unsupported runtime: {runtime_name}")
    
    registry = SUPPORTED_RUNTIMES[runtime_name]
    api_base = registry["api_base"]
    
    try:
        url = f"{api_base}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                raise Exception(f"Ollama API returned status {response.status}")
            
            data = json.loads(response.read().decode('utf-8'))
            models = [model.get("name", "") for model in data.get("models", [])]
            return [m for m in models if m]
    except urllib.error.URLError as e:
        raise Exception(f"Could not connect to Ollama at {api_base}. Is Ollama running? {e}")
    except Exception as e:
        raise Exception(f"Failed to list models: {e}")


def pull_model(model: str, runtime_name: str = "ollama") -> bool:
    """
    Pull model via runtime (explicit user action).
    
    Args:
        model: Model name to pull
        runtime_name: Runtime to use (default: "ollama")
        
    Returns:
        True if successful, False otherwise
    """
    if runtime_name not in SUPPORTED_RUNTIMES:
        logger.error(f"Unsupported runtime: {runtime_name}")
        return False
    
    registry = SUPPORTED_RUNTIMES[runtime_name]
    binary = registry["binary"]
    
    try:
        logger.info(f"Pulling model {model} via {binary}...")
        result = subprocess.run(
            [binary, "pull", model],
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully pulled model {model}")
            return True
        else:
            logger.error(f"Failed to pull model {model}: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout while pulling model {model}")
        return False
    except Exception as e:
        logger.error(f"Error pulling model {model}: {e}")
        return False


def validate_model(model: str, runtime_name: str = "ollama") -> bool:
    """
    Check if model exists locally.
    
    Args:
        model: Model name to validate
        runtime_name: Runtime to check (default: "ollama")
        
    Returns:
        True if model exists, False otherwise
    """
    try:
        available_models = list_available_models(runtime_name)
        return model in available_models
    except Exception:
        return False

