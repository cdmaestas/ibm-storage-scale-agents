"""Orchestrator Agent for coordinating multiple specialized agents."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from src.utils.common import load_agent_config
from src.utils.constants import (
    AGENT_METADATA,
    AGENT_TYPE_ILM,
    AGENT_TYPE_PROVISIONING,
    ILM_ALLOWED_TOOLS,
    ORCHESTRATOR_SYSTEM_PROMPT,
    PROVISIONING_ALLOWED_TOOLS,
)

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Agent for coordinating multiple specialized agents."""

    def __init__(
        self,
        config_path: str = "config/agents_settings.ini",
        agent_registry: Optional[Dict[str, Any]] = None,
    ):
        """Initialize orchestrator agent.
        
        Args:
            config_path: Path to configuration file
            agent_registry: Dictionary mapping agent types to agent instances
        """
        self.config, self.llm, self.mcp_client = load_agent_config(
            Path(config_path), "logs/agents.log"
        )
        self.agent_executor = None
        self.tools: List = []
        self.agent_registry = agent_registry or {}

    def set_agent_registry(self, agent_registry: Dict[str, Any]):
        """Set the agent registry after initialization.
        
        Args:
            agent_registry: Dictionary mapping agent types to agent instances
        """
        self.agent_registry = agent_registry
        logger.info(f"Agent registry updated with {len(agent_registry)} agents")

    async def initialize(self):
        """Initialize the orchestrator agent."""
        logger.info("Initializing Orchestrator Agent")

        # Create orchestrator-specific tools
        self.tools = [
            self._create_list_all_tools_tool(),
            self._create_get_agent_info_tool(),
            self._create_delegate_to_agent_tool(),
        ]

        memory = MemorySaver()
        self.agent_executor = create_react_agent(self.llm, self.tools, checkpointer=memory)

        # Format system prompt with tool lists
        provisioning_tools = ", ".join(PROVISIONING_ALLOWED_TOOLS)
        ilm_tools = ", ".join(ILM_ALLOWED_TOOLS)
        self.system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
            provisioning_tools=provisioning_tools, ilm_tools=ilm_tools
        )

        logger.info("Orchestrator Agent initialized")

    def _create_list_all_tools_tool(self) -> StructuredTool:
        """Create tool for listing all available tools across agents."""

        class ListAllToolsInput(BaseModel):
            """Input for list_all_tools - no parameters needed."""
            pass

        async def list_all_tools() -> str:
            """List all available tools across all specialized agents."""
            tools_info = {
                "provisioning_agent": {
                    "name": AGENT_METADATA[AGENT_TYPE_PROVISIONING]["name"],
                    "tools": AGENT_METADATA[AGENT_TYPE_PROVISIONING]["tools"],
                    "description": AGENT_METADATA[AGENT_TYPE_PROVISIONING]["description"],
                },
                "ilm_agent": {
                    "name": AGENT_METADATA[AGENT_TYPE_ILM]["name"],
                    "tools": AGENT_METADATA[AGENT_TYPE_ILM]["tools"],
                    "description": AGENT_METADATA[AGENT_TYPE_ILM]["description"],
                },
            }
            return json.dumps(tools_info, indent=2)

        return StructuredTool(
            name="list_all_tools",
            description="List all available tools across all specialized agents (Provisioning and ILM)",
            args_schema=ListAllToolsInput,
            coroutine=list_all_tools,
        )

    def _create_get_agent_info_tool(self) -> StructuredTool:
        """Create tool for getting information about a specific agent."""

        class GetAgentInfoInput(BaseModel):
            agent_type: str = Field(
                description=f"Agent type: '{AGENT_TYPE_PROVISIONING}' or '{AGENT_TYPE_ILM}'"
            )

        async def get_agent_info(agent_type: str) -> str:
            """Get detailed information about a specific agent's capabilities."""
            if agent_type not in AGENT_METADATA:
                return json.dumps(
                    {
                        "error": f"Unknown agent type: {agent_type}",
                        "available_types": list(AGENT_METADATA.keys()),
                    }
                )

            return json.dumps(AGENT_METADATA[agent_type], indent=2)

        return StructuredTool(
            name="get_agent_info",
            description="Get detailed information about a specific agent's capabilities",
            args_schema=GetAgentInfoInput,
            coroutine=get_agent_info,
        )

    def _create_delegate_to_agent_tool(self) -> StructuredTool:
        """Create tool for delegating tasks to specialized agents."""

        class DelegateToAgentInput(BaseModel):
            agent_type: str = Field(
                description=f"Agent type to delegate to: '{AGENT_TYPE_PROVISIONING}' or '{AGENT_TYPE_ILM}'"
            )
            task: str = Field(description="The task/query to delegate to the agent")

        async def delegate_to_agent(agent_type: str, task: str) -> str:
            """Delegate a task to a specialized agent and return the result.
            
            This enables agent-to-agent communication by allowing the orchestrator
            to invoke other agents and get their responses.
            """
            if agent_type not in self.agent_registry:
                return json.dumps(
                    {
                        "error": f"Agent type '{agent_type}' not found in registry",
                        "available_agents": list(self.agent_registry.keys()),
                    }
                )

            agent = self.agent_registry[agent_type]
            logger.info(f"Delegating task to {agent_type} agent: {task}")

            try:
                # Create a message for the delegated agent
                messages = [
                    SystemMessage(content=agent.system_prompt),
                    HumanMessage(content=task),
                ]

                # Prepare initial state based on agent type
                if agent_type == "ilm":
                    # ILM agent requires full workflow state
                    from src.ilm_agent.workflow_graph import create_initial_state
                    initial_state = create_initial_state()
                    initial_state["messages"] = messages
                else:
                    # Other agents just need messages
                    initial_state = {"messages": messages}

                # Execute the delegated agent
                result_messages = []
                async for event in agent.agent_executor.astream(
                    initial_state,
                    config={"configurable": {"thread_id": f"orchestrator-delegate-{agent_type}"}},
                    stream_mode="values",
                ):
                    if event and "messages" in event:
                        result_messages = event["messages"]

                # Extract the final response
                if result_messages:
                    for msg in reversed(result_messages):
                        if type(msg).__name__ == "AIMessage" and hasattr(msg, "content") and msg.content:
                            logger.info(f"Delegation to {agent_type} completed successfully")
                            return json.dumps(
                                {
                                    "agent": agent_type,
                                    "status": "success",
                                    "response": msg.content,
                                }
                            )

                return json.dumps(
                    {"agent": agent_type, "status": "error", "message": "No response from agent"}
                )

            except Exception as e:
                error_msg = f"Error delegating to {agent_type}: {str(e)}"
                logger.error(error_msg)
                return json.dumps({"agent": agent_type, "status": "error", "message": error_msg})

        return StructuredTool(
            name="delegate_to_agent",
            description="Delegate a task to a specialized agent (Provisioning or ILM) and get the result",
            args_schema=DelegateToAgentInput,
            coroutine=delegate_to_agent,
        )

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
