"""Pydantic models for normalized resources."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ResourceAction(str, Enum):
    """Normalized resource action types."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    READ = "READ"
    NO_OP = "NO_OP"


class NormalizedResource(BaseModel):
    """Provider-agnostic normalized resource model."""
    id: str = Field(..., description="Resource identifier without module prefix")
    module: Optional[str] = Field(None, description="Module path if resource is in a module")
    type: str = Field(..., description="Resource type/provider")
    action: ResourceAction = Field(..., description="Normalized action type")
    depends_on: List[str] = Field(default_factory=list, description="List of resource addresses this depends on")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class NormalizedPlan(BaseModel):
    """Normalized Terraform plan - collection of normalized resources."""
    resources: List[NormalizedResource] = Field(default_factory=list, description="List of normalized resources")
    
    class Config:
        """Pydantic config."""
        use_enum_values = True

