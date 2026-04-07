# Orchestrator Agent — Tools & Prompts Reference

This document describes the tools supported by the **Scale Orchestrator Agent** and provides example prompts you can use in the interactive CLI.

## Overview

The Orchestrator Agent is a meta-agent that coordinates between specialized agents to handle complex, multi-step workflows and provide unified access to all system capabilities.

## Supported Tools

All orchestrator tools execute immediately without confirmation, as they perform coordination and information retrieval operations.

### Meta-Query Tools

| Tool | Description |
|------|-------------|
| `list_all_tools` | List all available tools across all specialized agents |
| `get_agent_info` | Get detailed information about a specific agent's capabilities |
| `delegate_to_agent` | Delegate a task to a specialized agent and return the result |

## Tool Parameters

### `list_all_tools`

| Parameter | Required | Description |
|-----------|----------|-------------|
| None | - | Returns information about all agents and their tools |

### `get_agent_info`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `agent_type` | Yes | Agent type to query: `ilm` or `provisioning` |

### `delegate_to_agent`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `agent_type` | Yes | Target agent type: `ilm` or `provisioning` |
| `task` | Yes | Task description to delegate to the agent |


## Agent Architecture

```
┌─────────────────────────────────────┐
│      Orchestrator Agent             │
│  (Coordination & Meta-queries)      │
└──────────┬──────────────────────────┘
           │
           ├──────────────┬─────────────┐
           │              │             │
    ┌──────▼─────┐  ┌─────▼──────┐      │
    │Provisioning│  │ ILM Agent  │      │
    │   Agent    │  │            │      │
    └────────────┘  └────────────┘      │
           │              │             │
           └──────────────┴─────────────┘
                     │
              ┌──────▼──────┐
              │ MCP Server  │
              └─────────────┘
```

## Example Prompts

### Tool Discovery

```
List all available tools
```

```
What tools do you have access to?
```

```
Show me all capabilities
```

### Agent Information

```
What can the ILM agent do?
```

```
Tell me about the provisioning agent
```

```
What are the capabilities of the ILM agent?
```

### Task Delegation

```
Create a fileset called 'data' and then apply an ILM policy to migrate old files
```

```
Show me all filesets and their associated policies
```

```
Create a fileset 'archive' and set up a policy to migrate files older than 90 days
```

## Agent Behavior Notes

### Automatic Routing

The orchestrator is automatically invoked when queries contain these keywords:
- `list tools`, `show tools`, `what tools`, `available tools`
- `what can you do`, `capabilities`
- `help`, `agents`, `what agents`
- Multi-agent workflow requests (e.g., "create fileset and apply policy")

### Delegation Strategy

The orchestrator analyzes requests and:
1. Determines which specialized agents are needed
2. Delegates tasks in the correct sequence
3. Waits for each agent to complete before proceeding
4. Aggregates results from multiple agents
5. Presents a unified response to the user

### Agent Information

Each specialized agent has:
- **Name**: Display name (e.g., "ILM", "Provisioning")
- **Tools**: List of available tool names
- **Description**: Brief description of agent purpose
- **Capabilities**: Detailed list of what the agent can do

### Coordination vs. Execution

The orchestrator **coordinates** work but does not directly execute storage operations. It:
- Routes queries to appropriate specialized agents
- Provides system-wide information and discovery
- Manages multi-agent workflows
- Does not require confirmation (coordination is non-destructive)

## Related Documentation

- [ILM Agent](../ilm_agent/README.md) - For ILM policy operations
- [Provisioning Agent](../provisioning_agent/README.md) - For fileset operations
- [IBM Storage Scale Documentation](https://www.ibm.com/docs/en/storage-scale) - Official documentation
