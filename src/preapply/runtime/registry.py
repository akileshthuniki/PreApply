"""Declarative capability registry for AI runtimes."""

SUPPORTED_RUNTIMES = {
    "ollama": {
        "binary": "ollama",
        "api_base": "http://localhost:11434",
        "default_models": ["llama3.2", "mistral", "codellama"],
        "model_sizes": {
            "llama3.2": "~4.7GB",
            "mistral": "~4.1GB",
            "codellama": "~3.8GB"
        }
    }
}

