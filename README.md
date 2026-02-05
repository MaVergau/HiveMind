# 🧠 HiveMind Agent

An intelligent agent built with **Microsoft Agent Framework** that manages and maintains markdown files based on user input (text messages, documents, voice input, etc.).

## Features

- ✅ **Create, Read, Update, Delete** markdown files
- 🔍 **Search** across all markdown files
- ➕ **Append** content to existing files
- 📋 **List** all markdown files
- 🤖 **AI-powered** organization and maintenance
- 💬 **Conversational** interface with persistent context

## Prerequisites

- Python 3.8 or higher
- Azure CLI (already logged in via `az login`)
- Azure AI Foundry project with a deployed model

## Setup

### 1. Install Dependencies

**Important:** The `--pre` flag is **REQUIRED** while Agent Framework is in preview.

```bash
pip install -r requirements.txt --pre
```

### 2. Configure Environment

The `.env` file has been pre-configured with your project endpoint:

```env
AZURE_PROJECT_ENDPOINT=https://grippy-resource.services.ai.azure.com/api/projects/grippy
AZURE_MODEL_DEPLOYMENT_NAME=gpt-4o
MARKDOWN_FILES_DIR=./markdown_files
```

**TODO:** Update `AZURE_MODEL_DEPLOYMENT_NAME` with your actual deployed model name.

### 3. Deploy a Model (if needed)

You can explore and deploy models in AI Toolkit:
- Open VS Code Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
- Run: `AI Toolkit: Open Model Catalog`
- Filter by Microsoft Foundry models
- Deploy a recommended model: `gpt-4o`, `gpt-5-chat`, or `claude-sonnet-4-5`

## Usage

Run the HiveMind agent:

```bash
python hivemind.py
```

### Example Commands

```
You: Create a new file called ideas.md with a list of project ideas
HiveMind: [Creates the file and confirms]

You: What files do I have?
HiveMind: [Lists all markdown files]

You: Add a new idea to ideas.md about building a knowledge graph
HiveMind: [Appends the content]

You: Search for "knowledge graph"
HiveMind: [Shows which files contain that term]

You: Show me the contents of ideas.md
HiveMind: [Displays the file contents]
```

## Available Tools

The agent has access to these tools for managing markdown files:

| Tool | Description |
|------|-------------|
| `list_markdown_files` | List all markdown files in the directory |
| `read_markdown_file` | Read the contents of a specific file |
| `create_markdown_file` | Create a new markdown file |
| `update_markdown_file` | Replace the entire content of a file |
| `append_to_markdown_file` | Add content to the end of a file |
| `delete_markdown_file` | Delete a markdown file |
| `search_markdown_files` | Search for text across all files |

## Model Recommendation

For this markdown management agent, I recommend:

- **gpt-4o**: Best balance of performance and cost, excellent for structured tasks
- **gpt-5-chat**: More advanced conversational capabilities
- **claude-sonnet-4-5**: Superior for complex reasoning and document understanding

All models are available in Microsoft Foundry and fully supported with Agent Framework.

## Project Structure

```
HiveMind/
├── hivemind.py          # Main agent application
├── requirements.txt     # Python dependencies
├── .env                 # Configuration (your values)
├── .env.example         # Configuration template
├── .gitignore          # Git ignore rules
├── README.md           # This file
└── markdown_files/     # Created automatically for markdown storage
```

## Next Steps

Ready for you to provide more context on the **knowledge graph** functionality you'd like to add! This foundation is set up and ready to be extended with:

- Graph relationships between markdown files
- Metadata extraction
- Semantic linking
- Custom indexing strategies
- And more...

## Authentication

The agent uses `DefaultAzureCredential` which automatically uses your existing `az login` session. No additional authentication setup needed!

---

Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) 🚀
