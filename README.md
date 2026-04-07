# IBM Storage Scale Agents

A collection of agents for managing IBM Storage Scale operations. Currently includes a provisioning agent.

## Overview

This collection currently includes the Scale Provisioning Agent, which provides a conversational interface for managing IBM Storage Scale filesets, snapshots, and other storage operations. Built with LangChain and LangGraph, the agents integrate with the IBM Storage Scale MCP (Model Context Protocol) server to execute operations safely with user approval.

## Prerequisites

- Python 3.12 or higher
- [IBM Storage Scale MCP Server](https://github.com/IBM/ibm-storage-scale-mcp-server) running and accessible
- Ollama with a compatible model (default: qwen3:latest)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/IBM/ibm-storage-scale-agents.git
cd ibm-storage-scale-agents
```

2. Install dependencies using uv:
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

## Configuration

Edit [`config/agents_settings.ini`](config/agents_settings.ini) to configure the agent:

### LLM Configuration
```ini
[llm]
model_name = ollama_chat/qwen3:latest
```

### MCP Server Configuration

**Option 1: HTTP Transport**
```ini
[mcp]
transport = http
url = http://127.0.0.1:8000/mcp
```

**Option 2: Stdio Transport**
```ini
[mcp]
transport = stdio
command = /path/to/uv
args = --directory /path/to/scale-mcp-server run scale-mcp-server --transport stdio
```

### Logging Configuration
```ini
[logging]
level = DEBUG
format = json
log_path = logs/agents.log
max_bytes = 10485760
backup_count = 5
```

**Note:** All agents write to a single shared log file (`logs/agents.log`) for easier debugging and log correlation.
## Available Agents

| Agent | Description | Documentation |
|-------|-------------|---------------|
| Provisioning Agent | Manages IBM Storage Scale filesets, snapshots, and storage operations | [README](src/provisioning_agent/README.md) |
| ILM Agent | Manages Information Lifecycle Management policies and operations | [README](src/ilm_agent/README.md) |

## Usage

### Starting the Agent

Run the interactive CLI:
```bash
python main.py
```

Or using uv:
```bash
uv run python main.py
```

## Troubleshooting

### MCP Connection Issues

1. Verify the MCP server is running and accessible

2. Check the transport configuration in [`agents_settings.ini`](config/agents_settings.ini)

3. Review the log file (`logs/agents.log`) for connection errors

### Model Not Found

Ensure Ollama is running and the model is available:
```bash
ollama list
ollama pull qwen3:latest
```

### Tool Execution Failures

Check that:
- The MCP server has proper IBM Storage Scale API credentials
- The Scale cluster is accessible from the MCP server
- Tool names match those exposed by the MCP server


## Reporting Issues and Feedback

For issues, questions, or feature requests, please open an issue in the repository.

## Contributing Code

Contributions are welcome via Pull Requests. Please submit your very first Pull Request against the Developer's Certificate of Origin (DCO) located at [DCO.md](DCO.md) using your name and email address.

1. **Fork the repository** and create a new branch for your feature or bug fix
2. **Make your changes** following the existing code style and conventions
3. **Test your changes** thoroughly to ensure they work as expected
4. **Submit a pull request** with a clear description of your changes
5. **Sign the DCO** by adding your name and email address to the DCO.md file in your pull request

## Disclaimer

This software is provided "as is" without any warranties of any kind, including, but not limited to their installation, use, or performance. We are not responsible for any damage or charges or data loss incurred with their use. You are responsible for reviewing and testing any scripts you run thoroughly before use in any production environment. This content is subject to change without notice.
