"""Prompt Contract v1 - deterministic prompt construction for AI advisors."""

from dataclasses import dataclass
from typing import List
from ..contracts.core_output import CoreOutput
from ..presentation.explainer import explain_overall_with_id


@dataclass
class PromptContract:
    """
    Prompt Contract v1 - defines what AI receives.
    
    This contract ensures:
    - AI only sees deterministic CoreOutput data
    - AI cannot affect risk, policy, or enforcement
    - Prompt construction is deterministic
    """
    risk_level: str
    explanation_id: str
    explanation_text: str
    recommendations: List[str]
    blast_radius_summary: str
    affected_count: int
    affected_components: List[str]
    
    def to_prompt_text(self, question: str) -> str:
        """
        Build prompt text from contract.
        
        Args:
            question: User's question
            
        Returns:
            Complete prompt text for LLM
        """
        # Build blast radius summary
        blast_summary = f"""
Blast Radius Summary:
- Risk Level: {self.risk_level}
- Blast Radius Score: {self.affected_count} resources affected
- Affected Components: {', '.join(self.affected_components) if self.affected_components else 'None'}
"""
        
        # Build recommendations section
        recs_text = "\n".join(f"- {rec}" for rec in self.recommendations) if self.recommendations else "None"
        
        # Build full prompt with explicit constraints
        prompt = f"""You are an AI advisor for PreApply, an infrastructure risk analysis tool.

CRITICAL CONSTRAINTS (NON-NEGOTIABLE):
- You are NOT allowed to change risk levels, scores, policy decisions, or enforcement outcomes.
- You are providing ADVISORY information only.
- All risk facts come from the deterministic analysis below.
- You cannot override or modify the analysis results.

DETERMINISTIC ANALYSIS RESULTS:
{blast_summary}

Explanation ID: {self.explanation_id}

Deterministic Explanation:
{self.explanation_text}

Recommendations:
{recs_text}

USER QUESTION:
{question}

Please provide advisory guidance based on the analysis above. Remember:
- You are advisory only
- You cannot change risk levels or policy decisions
- Base your response on the deterministic facts provided
- If you need more information, state that clearly
"""
        return prompt


def build_prompt(core_output: CoreOutput, question: str) -> str:
    """
    Build prompt from CoreOutput (deterministic).
    
    This function is deterministic: same CoreOutput + same question = same prompt.
    
    Args:
        core_output: CoreOutput from analysis
        question: User's question
        
    Returns:
        Prompt text for LLM
    """
    # Get deterministic explanation
    explanation_text, explanation_id = explain_overall_with_id(core_output)
    
    # Build prompt contract
    contract = PromptContract(
        risk_level=str(core_output.risk_level),
        explanation_id=str(explanation_id.value if hasattr(explanation_id, 'value') else explanation_id),
        explanation_text=explanation_text,
        recommendations=core_output.recommendations,
        blast_radius_summary=f"{core_output.affected_count} resources affected, score: {core_output.blast_radius_score}",
        affected_count=core_output.affected_count,
        affected_components=core_output.affected_components
    )
    
    return contract.to_prompt_text(question)
