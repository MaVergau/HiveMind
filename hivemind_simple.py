"""
Simple HiveMind Knowledge Chat - Works without Agent Framework issues
Uses Azure OpenAI directly with function calling
"""

import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
import json

from knowledge_tools import (
    list_knowledge_categories,
    query_knowledge_category,
    search_knowledge,
    find_entity_knowledge,
    get_knowledge_summary
)

load_dotenv()

# Initialize Azure OpenAI
client = AzureOpenAI(
    azure_endpoint="https://grippy-resource.cognitiveservices.azure.com/",
    api_version="2024-05-01-preview",
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
)

# Define tools for function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search for information across the knowledge base. Use this when the user asks about people, organizations, or topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g., 'Caroline', 'Azure', 'Proximus')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_entity_knowledge",
            "description": "Find detailed information about a specific person, organization, or technology",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["people", "organizations", "technologies", "topics"],
                        "description": "Type of entity to search for"
                    },
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity"
                    }
                },
                "required": ["entity_type", "entity_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge_category",
            "description": "List all items in a specific category",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["people", "organizations", "technologies", "meetings", "topics"],
                        "description": "Category to query"
                    }
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_summary",
            "description": "Get an overview of the entire knowledge base",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

# Available functions
available_functions = {
    "search_knowledge": search_knowledge,
    "find_entity_knowledge": find_entity_knowledge,
    "query_knowledge_category": query_knowledge_category,
    "get_knowledge_summary": get_knowledge_summary
}

def chat(user_message, conversation_history):
    """Send message and handle function calls"""
    
    messages = conversation_history + [{"role": "user", "content": user_message}]
    
    # First API call
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=tools,
        temperature=0.7
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    
    # If no tool calls, return the response
    if not tool_calls:
        return response_message.content, messages + [{"role": "assistant", "content": response_message.content}]
    
    # Add assistant's message to conversation
    messages.append(response_message)
    
    # Execute function calls
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        print(f"  🔧 Calling: {function_name}({function_args})")
        
        function_to_call = available_functions[function_name]
        function_response = function_to_call(**function_args)
        
        # Add function response to messages
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": function_name,
            "content": function_response
        })
    
    # Second API call with function results
    second_response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0.7
    )
    
    final_message = second_response.choices[0].message.content
    messages.append({"role": "assistant", "content": final_message})
    
    return final_message, messages


def main():
    print("🧠 HiveMind Knowledge Chat")
    print("💡 Using Azure OpenAI GPT-4 with function calling")
    print("📁 Knowledge Base: 6 people, 22 orgs, 108 technologies, 3 meetings")
    print("\nType 'exit' to quit\n")
    
    system_message = {
        "role": "system",
        "content": """You are HiveMind, an AI assistant with access to a knowledge base about Proximus customer account.

When users ask about people, organizations, technologies, or meetings:
1. Use search_knowledge for general queries
2. Use find_entity_knowledge for specific people/orgs
3. Use query_knowledge_category to list all items in a category
4. Use get_knowledge_summary for overview

Be conversational and helpful. Always cite the knowledge base when answering."""
    }
    
    conversation = [system_message]
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ["exit", "quit", "q"]:
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        print("HiveMind: ", end="", flush=True)
        
        try:
            response, conversation = chat(user_input, conversation)
            print(response)
            print()
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    main()
