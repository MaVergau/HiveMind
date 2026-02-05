# 🧠 HiveMind - AI-Powered Knowledge Management Agent

> Intelligent knowledge extraction and querying system using Azure OpenAI GPT-4 and Microsoft Agent Framework

## Overview

HiveMind is an AI-powered knowledge management system that:
- **Extracts** structured knowledge from documents using GPT-4
- **Stores** information as human-readable markdown with YAML frontmatter
- **Queries** the knowledge base through an interactive AI agent
- **Maintains** temporal awareness and entity relationships

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Raw Input Documents                       │
│  (LinkedIn, PDFs, Meeting Notes, DOCX, Markdown)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         ai_knowledge_builder.py (GPT-4 Extraction)          │
│  • Intelligent entity recognition                            │
│  • Person/org/tech/topic extraction                          │
│  • Deduplication and structuring                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│             Knowledge Base (markdown_files/)                 │
│  entities/                     events/                       │
│    people/                       meetings/                   │
│    organizations/                decisions/                  │
│    technologies/                 milestones/                 │
│    topics/                                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           knowledge_tools.py (Query Interface)               │
│  • search_knowledge()                                        │
│  • find_entity_knowledge()                                   │
│  • query_knowledge_category()                                │
│  • get_knowledge_summary()                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              hivemind.py (Interactive Agent)                 │
│  Microsoft Agent Framework + Azure OpenAI GPT-4              │
│  Conversational interface to query knowledge base            │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```powershell
# 1. Build knowledge base from documents
python ai_knowledge_builder.py

# 2. Query with interactive agent
python hivemind.py
```

## Setup

### Prerequisites

- Python 3.11+
- Azure subscription with Azure OpenAI GPT-4 deployment
- Azure CLI (`az login` completed)

### Installation

```powershell
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Azure details
```

### Configuration (`.env`)

```bash
AZURE_PROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project
AZURE_MODEL_DEPLOYMENT_NAME=gpt-4.1
MARKDOWN_FILES_DIR=./markdown_files
```

## Usage

### Build Knowledge Base

```powershell
python ai_knowledge_builder.py
```

Processes documents from `RawInput/` using GPT-4:
- ✅ Markdown - LinkedIn profiles, meeting notes
- ✅ PDF - Strategic documents, reports
- ⚠️ DOCX - Transcripts (limited)

### Query Knowledge

```powershell
python hivemind.py
```

Example conversation:
```
You: Who are the key people at Proximus?
HiveMind: [Lists 6 people with roles]

You: Tell me about Caroline Van Cromphaut
HiveMind: Caroline Van Cromphaut is Head of IT Delivery: 
         Servicing & Integration at Proximus Group...
```

### Reset Knowledge Base

```powershell
python reset_knowledge_base.py
```

## Current Knowledge Base

| Category | Count | Examples |
|----------|-------|----------|
| **People** | 6 | Caroline Van Cromphaut, Dave Van Geel, Steven Pals |
| **Organizations** | 22 | Proximus, Nokia, Oracle, Teradata |
| **Technologies** | 108 | Azure, 5G, AI, Copilot, Databricks |
| **Meetings** | 5 | Account team meetings, NNR sessions |

## File Structure

```
HiveMind/
├── ai_knowledge_builder.py      # GPT-4 extraction engine
├── knowledge_tools.py            # Query API
├── hivemind.py                   # Main agent
├── hivemind_simple.py            # Alternative (direct OpenAI)
├── reset_knowledge_base.py       # Reset utility
├── requirements.txt
├── .env
├── RawInput/                     # Source documents
└── markdown_files/               # Generated KB
    ├── entities/
    │   ├── people/
    │   ├── organizations/
    │   ├── technologies/
    │   └── topics/
    └── events/
        ├── meetings/
        ├── decisions/
        └── milestones/
```

## Key Features

🤖 **AI-Powered** - GPT-4 intelligently extracts entities  
📚 **Human-Readable** - Markdown with YAML frontmatter  
🔍 **Smart Queries** - Natural language search  
⏰ **Temporal** - Time-aware knowledge tracking  
🔗 **Relationships** - Entity connections maintained  

## API Usage

```python
from knowledge_tools import search_knowledge, find_entity_knowledge

# Search
results = search_knowledge("Caroline")

# Find specific person
person = find_entity_knowledge("people", "Caroline Van Cromphaut")
```

## Performance

- **Input**: 18 MD + 9 PDFs + 9 DOCX
- **AI Calls**: 12 GPT-4 extractions
- **Processing**: ~30 seconds
- **Accuracy**: 100% (6/6 people vs 564 false positives with regex)

## Troubleshooting

**Agent can't find entities**: Run `python ai_knowledge_builder.py` first

**DOCX errors**: Convert to markdown or PDF first

**Auth errors**: Run `az login`

## Technology

- Azure OpenAI GPT-4
- Microsoft Agent Framework
- Python 3.11
- PyPDF, python-docx
- Azure Identity

---

**Built with ❤️ using Azure OpenAI GPT-4**
