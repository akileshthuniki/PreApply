"""Report generation module - read-only output surfaces for PreApply results."""

from .github import format_github_comment, post_pr_comment
from .markdown import generate_markdown
from .artifact import generate_artifacts

__all__ = [
    "format_github_comment",
    "post_pr_comment",
    "generate_markdown",
    "generate_artifacts",
]
