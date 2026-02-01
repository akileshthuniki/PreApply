"""AI Advisor module - read-only advisory AI that consumes CoreOutput."""

from .base import AIAdvisor
from .prompt import build_prompt, PromptContract

__all__ = [
    "AIAdvisor",
    "build_prompt",
    "PromptContract",
]
