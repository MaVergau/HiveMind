# HiveMind Quick Reference

## Daily Workflow

### 1️⃣ Add New Documents
```powershell
# Place documents in RawInput/
cp new-document.md RawInput/
cp meeting-transcript.pdf RawInput/
```

### 2️⃣ Rebuild Knowledge Base
```powershell
python ai_knowledge_builder.py
```

### 3️⃣ Query Knowledge
```powershell
python hivemind.py
```

## Common Commands

### Knowledge Building
```powershell
# Full rebuild (uses GPT-4)
python ai_knowledge_builder.py

# Reset and rebuild
python reset_knowledge_base.py
python ai_knowledge_builder.py
```

### Testing
```powershell
# Test query tools
python test_knowledge.py

# Quick search test
python -c "from knowledge_tools import search_knowledge; print(search_knowledge('Azure'))"
```

## File Locations

```
RawInput/               → Place source documents here
markdown_files/         → Generated knowledge base
  entities/people/      → Person profiles
  entities/organizations/ → Company info
  entities/technologies/  → Tech references
  events/meetings/      → Meeting records
```

## Common Queries

```
# People
"Who are the key people?"
"Tell me about [name]"
"What does [name] work on?"

# Organizations
"What organizations are we working with?"
"Tell me about Proximus"

# Technologies  
"What technologies are mentioned?"
"What do we know about Azure?"

# Meetings
"What meetings happened in November?"
"Summarize recent meetings"

# General
"Give me an overview"
"Search for [topic]"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent doesn't find entities | Run `python ai_knowledge_builder.py` first |
| "No results found" | Check spelling, try broader search |
| DOCX errors | Convert to PDF or markdown |
| Auth errors | Run `az login` |
| Slow response | GPT-4 is processing, be patient |

## Tips

✅ **DO**
- Add documents to RawInput/ before building
- Use descriptive filenames
- Run full rebuild after major changes
- Ask specific questions to the agent

❌ **DON'T**
- Manually edit markdown_files/ (regenerate instead)
- Delete templates (TEMPLATE.md files)
- Run builder too frequently (uses GPT-4 API calls)

## Configuration

Edit `.env` for:
- Azure OpenAI endpoint
- Model deployment name  
- Markdown directory path

## API Limits

Each full rebuild:
- ~12 GPT-4 API calls
- ~24K tokens (input + output)
- ~30 seconds processing time

Cost: Approximately $0.50-1.00 per rebuild (GPT-4 pricing)
