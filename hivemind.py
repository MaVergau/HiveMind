"""
HiveMind Agent - Markdown File Management with Microsoft Agent Framework

This agent helps you manage and maintain markdown files based on user input,
including text messages, documents, and voice input.
"""

import asyncio
import os
from pathlib import Path
from typing import Annotated

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Import knowledge system tools
from knowledge_tools import (
    list_knowledge_categories,
    query_knowledge_category,
    query_temporal_knowledge,
    search_knowledge,
    find_entity_knowledge,
    get_knowledge_summary
)


# Load environment variables
load_dotenv()

# Configuration
PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_MODEL_DEPLOYMENT_NAME")
MARKDOWN_DIR = Path(os.getenv("MARKDOWN_FILES_DIR", "./markdown_files"))

# Convert Foundry project endpoint to Azure OpenAI endpoint
# Extract the resource name from the Foundry endpoint
def get_azure_openai_endpoint(foundry_endpoint: str) -> str:
    """Convert Foundry project endpoint to Azure OpenAI endpoint format."""
    # Extract resource name from https://grippy-resource.services.ai.azure.com/api/projects/grippy
    # Should become https://grippy-resource.openai.azure.com/
    import re
    match = re.match(r"https://([^.]+)\.services\.ai\.azure\.com", foundry_endpoint)
    if match:
        resource_name = match.group(1)
        return f"https://{resource_name}.openai.azure.com/"
    else:
        # Fallback: assume it's already in the correct format
        return foundry_endpoint

AZURE_OPENAI_ENDPOINT = get_azure_openai_endpoint(PROJECT_ENDPOINT) if PROJECT_ENDPOINT else None


# Markdown file management tools
def list_markdown_files() -> str:
    """List all markdown files in the markdown directory."""
    if not MARKDOWN_DIR.exists():
        return "No markdown directory found. Use create_markdown_file to create your first file."
    
    md_files = list(MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        return "No markdown files found in the directory."
    
    file_list = "\n".join([f"- {f.name}" for f in sorted(md_files)])
    return f"Found {len(md_files)} markdown file(s):\n{file_list}"


def read_markdown_file(
    filename: Annotated[str, "The name of the markdown file to read (e.g., 'notes.md')"]
) -> str:
    """Read the contents of a markdown file."""
    file_path = MARKDOWN_DIR / filename
    
    if not file_path.exists():
        return f"File '{filename}' not found."
    
    try:
        content = file_path.read_text(encoding="utf-8")
        return f"Contents of {filename}:\n\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def create_markdown_file(
    filename: Annotated[str, "The name of the markdown file to create (e.g., 'notes.md')"],
    content: Annotated[str, "The initial content for the markdown file"]
) -> str:
    """Create a new markdown file with the given content."""
    # Ensure directory exists
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    
    file_path = MARKDOWN_DIR / filename
    
    if file_path.exists():
        return f"File '{filename}' already exists. Use update_markdown_file to modify it."
    
    try:
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully created '{filename}' with {len(content)} characters."
    except Exception as e:
        return f"Error creating file: {str(e)}"


def update_markdown_file(
    filename: Annotated[str, "The name of the markdown file to update (e.g., 'notes.md')"],
    content: Annotated[str, "The new content for the markdown file"]
) -> str:
    """Update an existing markdown file with new content."""
    file_path = MARKDOWN_DIR / filename
    
    if not file_path.exists():
        return f"File '{filename}' not found. Use create_markdown_file to create it first."
    
    try:
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully updated '{filename}' with {len(content)} characters."
    except Exception as e:
        return f"Error updating file: {str(e)}"


def append_to_markdown_file(
    filename: Annotated[str, "The name of the markdown file to append to (e.g., 'notes.md')"],
    content: Annotated[str, "The content to append to the file"]
) -> str:
    """Append content to an existing markdown file."""
    file_path = MARKDOWN_DIR / filename
    
    if not file_path.exists():
        return f"File '{filename}' not found. Use create_markdown_file to create it first."
    
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n{content}")
        return f"Successfully appended {len(content)} characters to '{filename}'."
    except Exception as e:
        return f"Error appending to file: {str(e)}"


def delete_markdown_file(
    filename: Annotated[str, "The name of the markdown file to delete (e.g., 'notes.md')"]
) -> str:
    """Delete a markdown file."""
    file_path = MARKDOWN_DIR / filename
    
    if not file_path.exists():
        return f"File '{filename}' not found."
    
    try:
        file_path.unlink()
        return f"Successfully deleted '{filename}'."
    except Exception as e:
        return f"Error deleting file: {str(e)}"


def search_markdown_files(
    query: Annotated[str, "The text to search for in markdown files"]
) -> str:
    """Search for text across all markdown files."""
    if not MARKDOWN_DIR.exists():
        return "No markdown directory found."
    
    md_files = list(MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        return "No markdown files to search."
    
    results = []
    for file_path in md_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            if query.lower() in content.lower():
                # Find the line containing the query
                lines = content.split("\n")
                matching_lines = [i + 1 for i, line in enumerate(lines) if query.lower() in line.lower()]
                results.append(f"- {file_path.name} (lines: {', '.join(map(str, matching_lines))})")
        except Exception:
            continue
    
    if not results:
        return f"No matches found for '{query}'."
    
    return f"Found '{query}' in {len(results)} file(s):\n" + "\n".join(results)


async def run_hivemind():
    """Main function to run the HiveMind agent."""
    
    if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT_NAME:
        print("Error: Please set AZURE_PROJECT_ENDPOINT and AZURE_MODEL_DEPLOYMENT_NAME in .env file")
        print("Copy .env.example to .env and fill in your values.")
        return
    
    # Define the agent's tools
    tools = [
        # Markdown file management
        list_markdown_files,
        read_markdown_file,
        create_markdown_file,
        update_markdown_file,
        append_to_markdown_file,
        delete_markdown_file,
        search_markdown_files,
        # Knowledge system tools
        list_knowledge_categories,
        query_knowledge_category,
        query_temporal_knowledge,
        search_knowledge,
        find_entity_knowledge,
        get_knowledge_summary,
    ]
    
    # Agent instructions
    instructions = """You are HiveMind, an intelligent agent specialized in managing knowledge and markdown files.

Your capabilities:

KNOWLEDGE BASE (Time-Aware Query System):
- Query knowledge by category (e.g., LinkedIn profiles, Meeting transcripts, Annual Reports)
- Search knowledge by time period (e.g., '2024', 'Q1 2025', 'January 2025')
- Find knowledge about specific entities (people, organizations, technologies)
- Full-text search across all ingested knowledge
- Get summaries and overviews of the knowledge base

MARKDOWN FILES (Active Working Documents):
- Create, read, update, and delete markdown files
- Search across markdown files
- Append content to existing files
- Organize and maintain markdown-based knowledge

WORKFLOW:
1. Use knowledge base tools to retrieve and analyze existing information
2. Use markdown tools to create structured outputs, summaries, and working documents
3. Help users synthesize knowledge from raw inputs into actionable insights

When responding to queries:
- First check the knowledge base for relevant information
- Provide temporal context when available (e.g., "According to Q1 2024 meeting...")
- Cross-reference multiple sources when answering
- Create markdown files to capture synthesized insights

Always be transparent about sources and provide clear summaries.
"""
    
    print("🧠 HiveMind Agent Starting...")
    print(f"📁 Markdown directory: {MARKDOWN_DIR.absolute()}")
    print(f"🤖 Model: {MODEL_DEPLOYMENT_NAME}")
    print(f"🔗 Azure OpenAI Endpoint: {AZURE_OPENAI_ENDPOINT}")
    print("\nType 'exit' to quit\n")
    
    # Create credential and chat client
    credential = DefaultAzureCredential()
    chat_client = AzureOpenAIChatClient(
        endpoint=AZURE_OPENAI_ENDPOINT,
        deployment_name=MODEL_DEPLOYMENT_NAME,
        credential=credential,
    )
    
    # Create the agent
    agent = ChatAgent(
        name="HiveMind",
        instructions=instructions,
        chat_client=chat_client,
        tools=tools,
    )
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if user_input.lower() in ["exit", "quit", "q"]:
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Stream the agent's response
        print("HiveMind: ", end="", flush=True)
        
        try:
            async for chunk in agent.run_stream(user_input):
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            
            print("\n")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    asyncio.run(run_hivemind())
