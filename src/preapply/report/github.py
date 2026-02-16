"""GitHub PR comment formatting and posting."""

import json
from typing import Optional
from pathlib import Path
import requests
from ..contracts.core_output import CoreOutput
from ..presentation.explainer import explain_overall_with_id
from ..utils.errors import PreApplyError
from ..utils.logging import get_logger

logger = get_logger("report.github")

# Marker to identify PreApply comments
COMMENT_MARKER = "<!-- preapply-report -->"


def format_github_comment(core_output: CoreOutput) -> str:
    """
    Format CoreOutput as GitHub markdown comment.
    
    Args:
        core_output: CoreOutput from analysis
        
    Returns:
        Formatted GitHub markdown comment string
    """
    # Get explanation with ID
    explanation, explanation_id = explain_overall_with_id(core_output)
    
    # Extract key signals (explanation IDs from risk attributes)
    key_signals = []
    attrs = core_output.risk_attributes
    
    if attrs.shared_dependencies:
        for dep in attrs.shared_dependencies:
            if dep.is_critical:
                key_signals.append("CRITICAL_SHARED_DEPENDENCY_MODIFICATION")
            else:
                key_signals.append("SHARED_DEPENDENCY_MODIFICATION")
    
    if attrs.critical_infrastructure:
        key_signals.append("CRITICAL_INFRASTRUCTURE_MODIFICATION")
    
    if "DELETE" in attrs.action_types:
        key_signals.append("DELETE_OPERATION_DETECTED")
    
    # Deduplicate signals
    key_signals = list(dict.fromkeys(key_signals))
    
    # Format risk level with emoji (use risk_level_detailed for display when available)
    risk_emoji = {
        "LOW": "✅",
        "MEDIUM": "⚠️",
        "HIGH": "❌",
        "HIGH-SEVERE": "❌",
        "CRITICAL": "🛑",
        "CRITICAL-CATASTROPHIC": "🛑",
    }
    display_level = getattr(core_output, "risk_level_detailed", None) or core_output.risk_level
    risk_level_display = f"{risk_emoji.get(str(display_level), '')} {display_level}"
    
    # Build comment
    comment_parts = [
        COMMENT_MARKER,
        "",
        "## PreApply Risk Assessment",
        "",
        f"**Risk Level:** {risk_level_display}",
        f"**Blast Radius:** {core_output.affected_count} resources / {core_output.blast_radius_score} score",
        ""
    ]
    
    # Key Signals section
    if key_signals:
        comment_parts.append("### Key Signals")
        comment_parts.append("")
        for signal in key_signals:
            comment_parts.append(f"- `{signal}`")
        comment_parts.append("")
    
    # Recommendations section
    if core_output.recommendations:
        comment_parts.append("### Recommendations")
        comment_parts.append("")
        for rec in core_output.recommendations:
            comment_parts.append(f"- {rec}")
        comment_parts.append("")
    
    # Detailed explanation in collapsible section
    comment_parts.extend([
        "<details>",
        "<summary>Deterministic Explanation</summary>",
        "",
        f"**Explanation ID:** `{explanation_id.value if hasattr(explanation_id, 'value') else explanation_id}`",
        "",
        explanation,
        "",
        "</details>"
    ])
    
    return "\n".join(comment_parts)


def post_pr_comment(
    repo: str,
    pr_number: int,
    comment: str,
    token: str,
    update: bool = False
) -> None:
    """
    Post comment to GitHub PR via REST API.
    
    Args:
        repo: Repository in format "owner/repo"
        pr_number: Pull request number
        comment: Comment body (markdown)
        token: GitHub personal access token
        update: If True, update existing comment instead of creating new one
        
    Raises:
        PreApplyError: If API call fails
    """
    # Parse repository
    if "/" not in repo:
        raise PreApplyError(f"Invalid repository format: {repo}. Expected 'owner/repo'")
    
    owner, repo_name = repo.split("/", 1)
    
    # API endpoint
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/{pr_number}/comments"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    # If update is requested, find existing comment
    if update:
        try:
            # Get existing comments
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            comments = response.json()
            
            # Find PreApply comment
            preapply_comment_id = None
            for comment_obj in comments:
                if COMMENT_MARKER in comment_obj.get("body", ""):
                    preapply_comment_id = comment_obj["id"]
                    break
            
            # Update existing comment if found
            if preapply_comment_id:
                update_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/comments/{preapply_comment_id}"
                update_response = requests.patch(
                    update_url,
                    headers=headers,
                    json={"body": comment}
                )
                update_response.raise_for_status()
                logger.info(f"Updated existing PreApply comment on PR #{pr_number}")
                return
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to check for existing comments: {e}")
            # Continue to create new comment
    
    # Create new comment
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json={"body": comment}
        )
        response.raise_for_status()
        logger.info(f"Posted PreApply comment to PR #{pr_number}")
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise PreApplyError("GitHub authentication failed. Check your GITHUB_TOKEN.")
        elif e.response.status_code == 404:
            raise PreApplyError(f"Repository or PR not found: {repo}#{pr_number}")
        else:
            error_msg = e.response.text if hasattr(e.response, 'text') else str(e)
            raise PreApplyError(f"GitHub API error: {error_msg}")
    
    except requests.exceptions.RequestException as e:
        raise PreApplyError(f"Failed to post GitHub comment: {e}")
