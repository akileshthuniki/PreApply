"""Abstract base class for AI advisors."""

from abc import ABC, abstractmethod
from typing import Optional
from ..contracts.core_output import CoreOutput


class AIAdvisor(ABC):
    """
    Abstract interface for AI advisors.
    
    AI advisors are read-only and advisory only. They cannot:
    - Affect risk scores or levels
    - Change policy decisions
    - Modify CoreOutput
    - Run implicitly
    
    They can only:
    - Consume CoreOutput JSON
    - Provide human-readable advisory text
    - Answer questions about the analysis
    """
    
    @abstractmethod
    def ask(
        self,
        core_output: CoreOutput,
        question: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Ask a question about the CoreOutput analysis.
        
        Args:
            core_output: CoreOutput from deterministic analysis
            question: User's question about the analysis
            max_tokens: Optional maximum tokens for response
            
        Returns:
            Human-readable advisory response (never affects CoreOutput)
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this AI provider is available.
        
        Returns:
            True if provider is configured and available
        """
        pass
