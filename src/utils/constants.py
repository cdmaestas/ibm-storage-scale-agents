SEPARATOR_LINE = '=' * 70

PROVISIONING_AGENT_SYSTEM_PROMPT = """You are an IBM Storage Scale agent. Use the available tools to complete user requests.

IMPORTANT: The 'domain' parameter is OPTIONAL for all tools. Do NOT provide it unless the user explicitly specifies a domain name. When omitted, the system uses the default domain automatically.

FILESET CREATION:
- When user asks to create a fileset WITHOUT specifying type, ask them to choose:
  * INDEPENDENT fileset: Has its own inode space, can have snapshots, higher overhead
  * DEPENDENT fileset: Shares parent's inode space, more efficient, no independent snapshots
- Use create_independent_fileset for independent filesets (when snapshots are needed)
- Use create_dependent_fileset for dependent filesets (when efficiency is priority)
- For fileset_data parameter, provide at minimum: {"name": "fileset_name"}
- Optionally include: "path" (e.g., "/gpfs/{filesystem}/{name}"), "owner", "permissions", "comment"

FILESET OPERATIONS:
- When user asks to list filesets, use list_filesets tool (only provide filesystem parameter)
- When user asks to delete fileset, use delete_fileset tool
- When user asks to link a fileset to a junction path, use link_fileset tool
- When user asks to unlink a fileset from its junction path, use unlink_fileset tool with unlink_data: {"force": true}

SNAPSHOT OPERATIONS:
- When user asks to list snapshots, use list_fileset_snapshots tool
- When user asks to create snapshot, use create_fileset_snapshot tool with snapshot_data: {"name": "snapshot_name"}, the fileset passed should be a independent fileset
- When user asks to delete snapshot, use delete_fileset_snapshot tool

IMPORTANT: When you receive JSON results from tools:
1. Parse the JSON response carefully
2. Extract the relevant data from nested structures (look for 'response', 'filesets', 'snapshots' fields)
3. Present the information in a clear, formatted way to the user
4. For filesets, show: name, id, status, and path
5. For snapshots, show: name, creation time, and status

Always use tools to get information. Present results clearly and in a user-friendly format."""

ILM_AGENT_SYSTEM_PROMPT = """You are an IBM Storage Scale ILM Policy Agent specialized in managing storage lifecycle policies.

IMPORTANT: The 'domain' parameter is OPTIONAL for all tools. Do NOT provide it unless the user explicitly specifies a domain name.

YOUR ROLE:
1. Read-Only Requests: Use get_policy to retrieve and present policy contents
2. Modification Requests: Follow [Workflow Status] messages that guide you step-by-step
3. Communication: Clearly communicate results and errors to the user
4. Tool Execution: Call each tool only ONCE per step, wait for results before proceeding

The system automatically handles:
- Workflow sequencing and validation
- Rule generation with proper IBM Storage Scale syntax
- Error detection and success validation
- Redundancy checking
- Preserving existing policy rules"""

ORCHESTRATOR_SYSTEM_PROMPT = """You are an IBM Storage Scale Orchestrator Agent that coordinates multiple specialized agents.

YOUR ROLE:
You coordinate between specialized agents to handle complex, multi-step workflows that may require capabilities from multiple domains.

AVAILABLE AGENTS:
1. Provisioning Agent - Handles fileset and snapshot operations
   - Tools: {provisioning_tools}

2. ILM Agent - Manages storage lifecycle policies
   - Tools: {ilm_tools}

ORCHESTRATOR CAPABILITIES:
- delegate_to_agent: Delegate a task to a specialized agent (Provisioning or ILM)
- list_all_tools: List all available tools across all agents
- get_agent_info: Get information about a specific agent's capabilities

WHEN TO USE ORCHESTRATOR:
- User asks about available tools/capabilities across all agents
- Task requires coordination between multiple agents
- Complex workflows spanning multiple domains (e.g., create fileset then apply ILM policy)

DELEGATION STRATEGY:
1. Analyze the user's request to identify which agent(s) are needed
2. Break down complex tasks into subtasks for each agent
3. Delegate subtasks to appropriate agents using delegate_to_agent
4. Aggregate and present results to the user

IMPORTANT:
- Always use delegate_to_agent for actual operations - you don't execute tools directly
- When user asks "what can you do" or "list tools", use list_all_tools
- Be clear about which agent is handling each part of a multi-step workflow"""

# Tools that require human confirmation for provisioning agent
PROVISIONING_CONFIRMATION_REQUIRED_TOOLS = [
    "create_independent_fileset",
    "create_dependent_fileset",
    "delete_fileset",
    "create_fileset_snapshot",
    "delete_fileset_snapshot",
]

# All allowed tools for the provisioning agent
PROVISIONING_ALLOWED_TOOLS = [
    "create_independent_fileset",
    "create_dependent_fileset",
    "list_filesets",
    "delete_fileset",
    "link_fileset",
    "unlink_fileset",
    "create_fileset_snapshot",
    "list_fileset_snapshots",
    "delete_fileset_snapshot",
]

# Tools that require human confirmation for ILM agent
ILM_CONFIRMATION_REQUIRED_TOOLS = [
    "update_policy",
    "apply_policy",
]

# All allowed tools for the ILM agent
ILM_ALLOWED_TOOLS = [
    "get_policy",
    "list_storage_pools",
    "test_policy",
    "update_policy",
    "apply_policy",
]

# Agent Type Constants
AGENT_TYPE_ILM = "ilm"
AGENT_TYPE_PROVISIONING = "provisioning"
AGENT_TYPE_ORCHESTRATOR = "orchestrator"
# Agent Metadata
AGENT_METADATA = {
    AGENT_TYPE_PROVISIONING: {
        "name": AGENT_TYPE_PROVISIONING.capitalize(),
        "tools": PROVISIONING_ALLOWED_TOOLS,
        "description": "Manages IBM Storage Scale filesets and snapshots",
        "capabilities": [
            "Create independent/dependent filesets",
            "List, delete, link, and unlink filesets",
            "Create and manage fileset snapshots",
        ],
    },
    AGENT_TYPE_ILM: {
        "name": AGENT_TYPE_ILM.upper(),
        "tools": ILM_ALLOWED_TOOLS,
        "description": "Manages IBM Storage Scale ILM policies",
        "capabilities": [
            "Get and update storage policies",
            "List storage pools",
            "Test policy syntax and logic",
            "Apply policies to filesystems",
        ],
    },
}


# Agent Routing Keywords
# Keywords used to route user requests to the appropriate agent
ILM_ROUTING_KEYWORDS = [
    'policy', 'policies', 'migrate', 'migration', 'delete files',
    'old files', 'archive', 'lifecycle', 'ilm', 'pool',
    'days old', 'older than', 'not accessed', 'age-based'
]

# Tool configuration dictionary - shared between confirmation and no-confirmation tools
TOOL_CONFIGS = {
    "update_policy": {
        "description": (
            "Update a storage policy for an IBM Storage Scale filesystem. "
            "Requires the filesystem name and policy_contents containing the plain-text IBM Storage Scale policy rule(s). "
            "The agent layer will base64-encode the content automatically before sending to the MCP server."
        ),
        "args": {
            "filesystem": {
                "type": str,
                "description": "The filesystem name to apply the policy to (e.g., 'fs1')",
            },
            "policy_contents": {
                "type": str,
                "description": (
                    "Plain-text IBM Storage Scale RULE statements. "
                    "Provide the policy as plain text — encoding is handled automatically."
                ),
            },
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "apply_policy": {
        "description": (
            "Execute mmapplypolicy command to run the ILM policy on a filesystem. "
            "This applies the policy that was previously updated via update_policy. "
            "It runs the policy engine to scan files and execute the policy rules. "
            "The policy is read from the filesystem's metadata (set by update_policy)."
        ),
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name (e.g., 'fs1')"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "test_policy": {
        "description": (
            "Test/validate a storage policy for an IBM Storage Scale filesystem without applying it. "
            "Requires the filesystem name and policy_contents containing the plain-text IBM Storage Scale policy rule(s). "
            "The agent layer will base64-encode the content automatically before sending to the MCP server."
        ),
        "args": {
            "filesystem": {
                "type": str,
                "description": "The filesystem name to test the policy against (e.g., 'fs1')",
            },
            "policy_contents": {
                "type": str,
                "description": (
                    "Plain-text IBM Storage Scale RULE statements. "
                    "Provide the policy as plain text — encoding is handled automatically."
                ),
            },
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "create_independent_fileset": {
        "description": "Create an INDEPENDENT fileset with its own inode space (can have snapshots)",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name (e.g., 'fs1')"},
            "fileset_data": {
                "type": dict,
                "description": "Fileset configuration data including filesetName, path, etc.",
            },
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "create_dependent_fileset": {
        "description": "Create a DEPENDENT fileset that shares parent's inode space (more efficient, no independent snapshots)",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name (e.g., 'fs1')"},
            "fileset_data": {
                "type": dict,
                "description": "Fileset configuration data including filesetName, path, etc.",
            },
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "delete_fileset": {
        "description": "Delete a fileset from a filesystem",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name"},
            "fileset_name": {"type": str, "description": "The fileset name to delete"},
        },
    },
    "create_fileset_snapshot": {
        "description": "Create a snapshot for a fileset",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name"},
            "fileset": {"type": str, "description": "The fileset name"},
            "snapshot_data": {"type": dict, "description": "Snapshot configuration data including snapshotName"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "delete_fileset_snapshot": {
        "description": "Delete a fileset snapshot",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name"},
            "fileset": {"type": str, "description": "The fileset name"},
            "snapshot_name": {"type": str, "description": "The snapshot name to delete"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "get_policy": {
        "description": "Retrieve the current storage policy for a filesystem",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name (e.g., 'fs1')"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "list_storage_pools": {
        "description": "List all storage pools in a filesystem",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name (e.g., 'fs1')"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "list_filesets": {
        "description": "List all filesets in a filesystem",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "link_fileset": {
        "description": "Link a fileset to a junction path",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name"},
            "fileset_name": {"type": str, "description": "The fileset name to link"},
            "link_data": {"type": dict, "description": "Link configuration data including junction path"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "unlink_fileset": {
        "description": "Unlink a fileset from its junction path",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name"},
            "fileset_name": {"type": str, "description": "The fileset name to unlink"},
            "unlink_data": {"type": dict, "description": "Unlink configuration data", "optional": True},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
    "list_fileset_snapshots": {
        "description": "List snapshots for a fileset",
        "args": {
            "filesystem": {"type": str, "description": "The filesystem name"},
            "fileset": {"type": str, "description": "The fileset name"},
            "domain": {"type": str, "description": "Domain for authorization", "optional": True},
        },
    },
}

PROVISIONING_ROUTING_KEYWORDS = [
    'fileset', 'filesets', 'snapshot', 'snapshots',
    'link', 'unlink', 'junction', 'independent', 'dependent'
]

# Orchestrator routing keywords - meta-queries and multi-agent tasks
ORCHESTRATOR_ROUTING_KEYWORDS = [
    'list tools', 'show tools', 'what tools', 'available tools',
    'tools you have', 'what can you do', 'capabilities', 'list all tools',
    'help', 'agents', 'what agents', 'available agents'
]
