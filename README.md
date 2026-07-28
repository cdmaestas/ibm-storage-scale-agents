# IBM Storage Scale Agents

A collection of agents for managing IBM Storage Scale operations, with a conversational interface over the IBM Storage Scale MCP server.

## Overview

This collection provides a conversational interface for managing IBM Storage Scale storage operations. It includes three cooperating agents:

- **Provisioning Agent** — filesets, snapshots, and related storage operations
- **ILM Agent** — Information Lifecycle Management policies (generate, test, update, and apply)
- **Orchestrator Agent** — coordinates the specialized agents for multi-step workflows

Built with LangChain and LangGraph, the agents integrate with the IBM Storage Scale MCP (Model Context Protocol) server to execute operations safely with user approval. A keyword router in [`main.py`](main.py) directs each request to the appropriate agent.

## Prerequisites

- Python 3.12 or higher
- [IBM Storage Scale MCP Server](https://github.com/IBM/ibm-storage-scale-mcp-server) running and accessible
- An LLM backend — any one of: Ollama (default), an OpenAI-compatible server (vLLM, LM Studio, …), OpenAI, Anthropic, Azure OpenAI, or AWS Bedrock. See [Connect your LLM](#connect-your-llm).

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

The base install supports **Ollama** out of the box. Other LLM providers are optional extras — install only what you need:

```bash
uv sync --extra openai      # OpenAI, vLLM, LM Studio, llama.cpp, Together, Groq (+ Azure)
uv sync --extra anthropic   # Anthropic Claude
uv sync --extra aws         # AWS Bedrock
# pip equivalent: pip install 'scale-agents[openai]'
```

## Configuration

Edit [`config/agents_settings.ini`](config/agents_settings.ini) to configure the agent.

### Connect your LLM

Select a backend with the `provider` key in the `[llm]` section. One `openai` provider covers every OpenAI-compatible server (OpenAI, vLLM, LM Studio, llama.cpp, Together, Groq, …).

| Provider | Extra needed | Typical config |
|----------|--------------|----------------|
| `ollama` | _(built in)_ | `base_url` (default `http://localhost:11434`) |
| `openai` | `openai` | `base_url` + API key (for vLLM etc., key is optional) |
| `anthropic` | `anthropic` | API key |
| `azure` | `openai` | `base_url` (endpoint) + `azure_api_version` + API key |
| `bedrock` | `aws` | `aws_region` + standard AWS credentials |

**API keys are read from the environment only** — never put them in the INI. Any setting can also be overridden by an environment variable named `SCALE_AGENTS_LLM_<KEY>`, which is what makes containerized/remote deployment easy.

**Local Ollama** (default):
```ini
[llm]
provider = ollama
model_name = qwen3:latest
base_url = http://localhost:11434
```

**Remote Ollama** — just point `base_url` at the host:
```ini
[llm]
provider = ollama
model_name = qwen3:latest
base_url = http://gpu-box.example.com:11434
```

**vLLM / any OpenAI-compatible server** (`uv sync --extra openai`):
```ini
[llm]
provider = openai
model_name = Qwen/Qwen2.5-7B-Instruct
base_url = http://vllm-host:8000/v1
```
```bash
export SCALE_AGENTS_LLM_API_KEY=...   # vLLM usually accepts any/empty value
```

**OpenAI** (`uv sync --extra openai`):
```ini
[llm]
provider = openai
model_name = gpt-4o
```
```bash
export SCALE_AGENTS_LLM_API_KEY=sk-...   # or OPENAI_API_KEY
```

**Anthropic** (`uv sync --extra anthropic`):
```ini
[llm]
provider = anthropic
model_name = <your-claude-model-id>
```
```bash
export SCALE_AGENTS_LLM_API_KEY=...   # or ANTHROPIC_API_KEY
```

**Azure OpenAI** (`uv sync --extra openai`):
```ini
[llm]
provider = azure
model_name = my-deployment-name
base_url = https://my-resource.openai.azure.com
azure_api_version = 2024-06-01
```
```bash
export SCALE_AGENTS_LLM_API_KEY=...   # or AZURE_OPENAI_API_KEY
```

**AWS Bedrock** (`uv sync --extra aws`, uses the standard AWS credential chain):
```ini
[llm]
provider = bedrock
model_name = anthropic.claude-3-5-sonnet-20240620-v1:0
aws_region = us-east-1
```

> Existing configs using the legacy `model_name = ollama_chat/qwen3:latest` prefix continue to work unchanged.

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
| Orchestrator Agent | Coordinates the specialized agents for multi-step workflows | [README](src/orchestrator_agent/README.md) |

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

### Run with Docker

The agents can run in a container, configured entirely through environment variables (no file editing required). Copy the env template and adjust it:

```bash
cp .env.example .env
# edit .env: pick your provider, model, base_url, and MCP server URL
```

Run the interactive CLI against an LLM and MCP server you already have:

```bash
docker compose run --rm agent
```

To also spin up a local Ollama alongside the agent, enable the `ollama` profile:

```bash
docker compose --profile ollama up -d ollama
docker compose --profile ollama exec ollama ollama pull qwen3:latest
docker compose --profile ollama run --rm agent
```

To bake in a non-Ollama provider, set the extras at build time:

```bash
SCALE_AGENTS_EXTRAS="--extra openai" docker compose build agent
```

> The IBM Storage Scale MCP server runs separately. Point `SCALE_AGENTS_MCP_URL` at it — use `http://host.docker.internal:8000/mcp` when it runs on the Docker host.

### Health check

Verify LLM and MCP connectivity without starting an interactive session. It lists the MCP server's tools and makes one minimal LLM request, prints a PASS/FAIL line per check, and exits `0`/`1`:

```bash
python main.py --healthcheck              # or: uv run python main.py --healthcheck
docker compose run --rm agent --healthcheck
```

Example output:
```
[healthcheck] MCP (http://127.0.0.1:8000/mcp): OK — 14 tools
[healthcheck] LLM (qwen3:latest): OK — responded 'OK'
[healthcheck] PASS
```

## Development

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting and [pre-commit](https://pre-commit.com/) to run checks automatically.

Install the git hooks (pre-commit and pre-push) once:
```bash
uvx pre-commit install --install-hooks -t pre-commit -t pre-push
```

Run the checks manually:
```bash
uvx ruff check .          # lint
uvx ruff format .         # format
uvx pre-commit run --all-files
```

Audit dependencies for known vulnerabilities:
```bash
uv run --with pip-audit pip-audit --skip-editable
```

The same checks (lint, format, import smoke test, dependency audit) run in CI on every pull request via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

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

### ILM Rule Generation Errors

The ILM Agent loads its policy syntax reference from
[`src/ilm_agent/policy_syntax_examples.md`](src/ilm_agent/policy_syntax_examples.md).
If this file is missing or empty, rule generation now fails immediately with a
clear error rather than silently producing invalid policy rules. Ensure the file
is present and non-empty.


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
