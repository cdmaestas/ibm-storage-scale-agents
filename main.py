"""Main entry point for IBM Storage Scale Agents."""

import asyncio
import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from src.ilm_agent.agent import ILMAgent
from src.ilm_agent.workflow_graph import create_initial_state
from src.orchestrator_agent.agent import OrchestratorAgent
from src.provisioning_agent.agent import ProvisioningAgent
from src.utils.constants import (
    AGENT_TYPE_ILM,
    AGENT_TYPE_ORCHESTRATOR,
    AGENT_TYPE_PROVISIONING,
    ILM_ROUTING_KEYWORDS,
    ORCHESTRATOR_ROUTING_KEYWORDS,
    PROVISIONING_ROUTING_KEYWORDS,
    SEPARATOR_LINE,
)

logger = logging.getLogger(__name__)
async def route_to_agent(user_input: str) -> str:
    """Use keyword-based routing to determine which agent should handle the request.
    
    Returns:
        Agent type constant (AGENT_TYPE_ORCHESTRATOR, AGENT_TYPE_ILM, or AGENT_TYPE_PROVISIONING)
    """
    user_input_lower = user_input.lower()
    keyword_mapping = [
        (AGENT_TYPE_ORCHESTRATOR, ORCHESTRATOR_ROUTING_KEYWORDS),
        (AGENT_TYPE_ILM, ILM_ROUTING_KEYWORDS),
        (AGENT_TYPE_PROVISIONING, PROVISIONING_ROUTING_KEYWORDS),
    ]
    for agent_type, keywords in keyword_mapping:
        for keyword in keywords:
            if keyword in user_input_lower:
                logger.debug(f"Routing to {agent_type} agent (matched keyword: '{keyword}')")
                return agent_type
    logger.debug(f"No clear keyword match. Defaulting to {AGENT_TYPE_PROVISIONING} agent.")
    return AGENT_TYPE_PROVISIONING


def get_interrupt_value(interrupt_list):
    """Extract interrupt value from interrupt list."""
    if interrupt_list and len(interrupt_list) > 0:
        interrupt_obj = interrupt_list[0]
        return interrupt_obj.value if hasattr(interrupt_obj, "value") else {}
    return {}


def get_user_approval(tool_name, arguments):
    """Display confirmation request and get user approval."""
    print(f"\n{SEPARATOR_LINE}")
    print(f"⚠️  CONFIRMATION REQUIRED: {tool_name}")
    print(f"{SEPARATOR_LINE}")
    print("Arguments:")
    print(json.dumps(arguments, indent=2))
    print(f"{SEPARATOR_LINE}")

    while True:
        approval_input = input("Approve? (yes/no): ").strip().lower()
        if approval_input in ["yes", "y"]:
            return True
        elif approval_input in ["no", "n"]:
            return False
        print("Please enter 'yes' or 'no'")


async def handle_interrupt(agent, event, config):
    """Handle interrupt and resume execution based on user approval.
    This function handles one interrupt at a time. After resuming, if there are
    more interrupts (e.g., apply_policy after update_policy), they will be handled
    by the main loop in run_agent.
    """
    interrupt_value = get_interrupt_value(event["__interrupt__"])
    tool_name = interrupt_value.get("tool_name", "unknown")
    arguments = interrupt_value.get("arguments", {})

    approved = get_user_approval(tool_name, arguments)

    if approved:
        print(f"✓ Approved. Executing {tool_name}...\n")
    else:
        print(f"✗ Cancelled. Operation {tool_name} not executed.\n")

    final_event = None
    async for resume_event in agent.agent_executor.astream(
        Command(resume={"approved": approved}), config=config, stream_mode="values"
    ):
        final_event = resume_event

        if final_event and "__interrupt__" in final_event:
            logger.debug(f"Another interrupt detected after {tool_name}, handling it...")
            final_event = await handle_interrupt(agent, final_event, config)
            break
    return final_event


async def run_agent(agent, user_input: str, config: dict, first_turn: bool = False):
    """Run a single agent turn and handle any interrupts."""
    interrupted = False
    event = None

    if first_turn:
        messages = [SystemMessage(content=agent.system_prompt), HumanMessage(content=user_input)]
    else:
        messages = [HumanMessage(content=user_input)]

    if first_turn and isinstance(agent, ILMAgent):
        initial_state = create_initial_state()
        initial_state["messages"] = messages  # type: ignore
        input_state = initial_state
    else:
        input_state = {"messages": messages}

    async for event in agent.agent_executor.astream(
        input_state,  # type: ignore
        config=config,
        stream_mode="values",
    ):
        if event and "messages" in event:
            messages_in_event = event.get("messages", [])
            if messages_in_event:
                last_msg = messages_in_event[-1]
                msg_type = type(last_msg).__name__
                
                if msg_type == "AIMessage" and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    for tool_call in last_msg.tool_calls:
                        logger.debug(f"Agent calling tool: {tool_call.get('name', 'unknown')}")

        if "__interrupt__" in event:
            interrupted = True
            event = await handle_interrupt(agent, event, config)
            if event and "messages" in event:
                messages_in_event = event.get("messages", [])
                for msg in messages_in_event:
                    if type(msg).__name__ == "AIMessage" and hasattr(msg, "content") and msg.content:
                        print(f"\nAgent: {msg.content}\n")
                        break

    # Show final response if not interrupted
    if not interrupted and event and "messages" in event:
        messages_in_event = event.get("messages", [])
        for msg in reversed(messages_in_event):
            if type(msg).__name__ == "AIMessage" and hasattr(msg, "content") and msg.content:
                print(f"\nAgent: {msg.content}\n")
                break


async def main():
    """Run interactive session with agent routing and orchestration."""
    print("IBM Storage Scale Intelligent Agent System")

    async with (
        ProvisioningAgent() as provisioning_agent,
        ILMAgent() as ilm_agent,
        OrchestratorAgent() as orchestrator_agent,
    ):
        agent_registry = {
            AGENT_TYPE_PROVISIONING: provisioning_agent,
            AGENT_TYPE_ILM: ilm_agent,
        }
        orchestrator_agent.set_agent_registry(agent_registry)
        print("Ready. Type 'quit' to exit.\n")

        provisioning_config = {"configurable": {"thread_id": "provisioning-main"}, "recursion_limit": 25}
        ilm_config = {"configurable": {"thread_id": "ilm-main"}, "recursion_limit": 25}
        orchestrator_config = {"configurable": {"thread_id": "orchestrator-main"}, "recursion_limit": 25}
        current_agent = None
        current_config = None
        first_turn = True

        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    break

                if not user_input:
                    continue

                route = await route_to_agent(user_input)
                

                if route == AGENT_TYPE_ORCHESTRATOR:
                    selected_agent = orchestrator_agent
                    selected_config = orchestrator_config
                    selected_label = f"{AGENT_TYPE_ORCHESTRATOR.capitalize()} Agent"
                elif route == AGENT_TYPE_ILM:
                    selected_agent = ilm_agent
                    selected_config = ilm_config
                    selected_label = f"{AGENT_TYPE_ILM.upper()} Agent"
                else:  # provisioning
                    selected_agent = provisioning_agent
                    selected_config = provisioning_config
                    selected_label = f"{AGENT_TYPE_PROVISIONING.capitalize()} Agent"
                
                if current_agent != selected_agent:
                    if current_agent is not None:
                        print(f"\n[Switching to {selected_label}]\n")
                    else:
                        print(f"[Routing to {selected_label}]\n")
                    first_turn = True
                    current_agent = selected_agent
                    current_config = selected_config

                # Run the selected agent
                await run_agent(current_agent, user_input, current_config, first_turn=first_turn)
                first_turn = False

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}\n")
                logger.exception("Error in main loop")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
