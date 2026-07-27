"""IBM Storage Scale ILM Policy Rule Generator using LLM"""

import logging
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# Load policy syntax documentation once at module level (context injection, not true RAG)
_SYNTAX_DOCS_PATH = Path(__file__).parent / "policy_syntax_examples.md"
_SYNTAX_DOCS_CONTENT = None


def _load_syntax_documentation() -> str:
    """Load policy syntax documentation from markdown file for context injection."""
    global _SYNTAX_DOCS_CONTENT
    if _SYNTAX_DOCS_CONTENT is None:
        try:
            _SYNTAX_DOCS_CONTENT = _SYNTAX_DOCS_PATH.read_text(encoding="utf-8")
            logger.debug(f"Loaded policy syntax documentation from {_SYNTAX_DOCS_PATH}")
        except OSError as e:
            # This markdown file is a required, shipped resource. Without it the
            # LLM has no syntax context and would silently emit invalid IBM
            # Storage Scale policy rules. Fail loudly instead of degrading.
            logger.error(f"Failed to load syntax documentation: {e}")
            raise RuntimeError(
                f"Required policy syntax documentation is missing or unreadable at {_SYNTAX_DOCS_PATH}: {e}"
            ) from e
        if not _SYNTAX_DOCS_CONTENT.strip():
            raise RuntimeError(
                f"Policy syntax documentation at {_SYNTAX_DOCS_PATH} is empty; "
                "cannot generate valid policy rules without it."
            )
    return _SYNTAX_DOCS_CONTENT


async def generate_ilm_rule_with_llm(
    llm,
    user_request: str,
    storage_pools: list[str],
    existing_policy_text: str,
    filesystem: str = "unknown",
) -> dict[str, Any]:
    """Generate ILM policy rule using LLM.

    Args:
        llm: Language model instance
        user_request: User's natural language request
        storage_pools: List of available storage pool names
        existing_policy_text: Existing policy content
        filesystem: Filesystem name

    Returns:
        Dictionary with rule_name and rule_content, or error
    """
    logger.debug("LLM based RULE generation")
    logger.debug(f"User request: {user_request}")
    logger.debug(f"Available pools: {', '.join(storage_pools)}")

    # Extract existing rule names
    existing_rules = []
    if existing_policy_text:
        for match in re.finditer(r"RULE\s+'([^']+)'", existing_policy_text, re.IGNORECASE):
            existing_rules.append(match.group(1))

    logger.debug(f"Existing rules: {', '.join(existing_rules) if existing_rules else 'None'}")

    # Load syntax documentation for context injection
    syntax_docs = _load_syntax_documentation()

    # Create prompt with documentation context and user-specific information
    prompt = f"""{syntax_docs}

USER REQUEST: {user_request}

AVAILABLE STORAGE POOLS: {", ".join(storage_pools)}

EXISTING POLICY:
{existing_policy_text if existing_policy_text else "No existing rules"}

AVOID THESE RULE NAMES: {", ".join(existing_rules) if existing_rules else "none"}

Generate ONLY the policy rule using the exact syntax from the examples above. Use only the available pools listed. No explanations."""

    logger.debug("Invoking LLM for policy rule generation with syntax documentation context...")
    logger.debug(f"Prompt length: {len(prompt)} characters")

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        rule_content = response.content.strip()

        logger.debug("LLM raw output (Generated Policy Rule):")
        logger.debug(rule_content)

        # Extract rule name
        rule_name_match = re.search(r"RULE\s+'([^']+)'", rule_content, re.IGNORECASE)
        rule_name = rule_name_match.group(1) if rule_name_match else "GeneratedRule"

        logger.debug(f"Extracted rule name: {rule_name}")
        logger.info(f"Rule generation completed: {rule_name}")

        return {
            "rule_name": rule_name,
            "rule_content": rule_content,
            "metadata": {
                "generated_by": "llm",
                "filesystem": filesystem,
                "available_pools": storage_pools,
                "existing_rules": existing_rules,
            },
        }

    except Exception as e:
        logger.error(f"LLM rule generation failed: {str(e)}")
        return {"error": f"LLM generation failed: {str(e)}"}
