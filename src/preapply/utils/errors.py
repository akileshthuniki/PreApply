"""Custom exception classes for PreApply."""


class PreApplyError(Exception):
    """Base exception for all PreApply errors."""
    pass


class PlanLoadError(PreApplyError):
    """Raised when Terraform plan JSON cannot be loaded or is invalid."""
    pass


class NormalizationError(PreApplyError):
    """Raised when plan normalization fails."""
    pass


class GraphConstructionError(PreApplyError):
    """Raised when dependency graph construction fails."""
    pass


class AnalysisError(PreApplyError):
    """Raised when risk analysis fails."""
    pass


class ConfigError(PreApplyError):
    """Raised when configuration is invalid or missing."""
    pass

