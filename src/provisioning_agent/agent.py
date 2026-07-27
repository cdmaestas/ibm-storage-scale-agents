"""Provisioning Agent for IBM Storage Scale operations."""

import logging
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.utils.common import (
    create_langchain_tool_no_confirmation_simple,
    create_langchain_tool_with_confirmation_simple,
    load_agent_config,
)
from src.utils.constants import (
    PROVISIONING_AGENT_SYSTEM_PROMPT,
    PROVISIONING_ALLOWED_TOOLS,
    PROVISIONING_CONFIRMATION_REQUIRED_TOOLS,
)

logger = logging.getLogger(__name__)


class ProvisioningAgent:
    """Agent for managing IBM Storage Scale filesets and snapshots."""

    def __init__(self, config_path: str = "config/agents_settings.ini"):
        self.config, self.llm, self.mcp_client = load_agent_config(
            Path(config_path),
            "logs/agents.log"
        )



        self.agent_executor = None
        self.tools: list = []

    async def initialize(self):
        """Initialize the agent and connect to MCP server."""
        logger.info(f"Allowed tools: {', '.join(PROVISIONING_ALLOWED_TOOLS)}")

        await self.mcp_client._ensure_session()
        logger.info("MCP server connected")

        logger.info("Configuring tools")
        for tool_name in PROVISIONING_ALLOWED_TOOLS:
            if tool_name in PROVISIONING_CONFIRMATION_REQUIRED_TOOLS:
                tool = create_langchain_tool_with_confirmation_simple(tool_name, self.mcp_client)
                logger.debug(f"Configured tool: {tool_name} (with confirmation)")
            else:
                tool = create_langchain_tool_no_confirmation_simple(tool_name, self.mcp_client)
                logger.debug(f"Configured tool: {tool_name}")

            self.tools.append(tool)

        memory = MemorySaver()
        self.agent_executor = create_react_agent(
            self.llm,
            self.tools,
            checkpointer=memory,
        )

        self.system_prompt = PROVISIONING_AGENT_SYSTEM_PROMPT
        logger.info("Agent initialized")

    async def cleanup(self):
        """Cleanup resources."""
        if self.mcp_client:
            await self.mcp_client.cleanup()
            logger.info("Cleaned up MCP client")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
