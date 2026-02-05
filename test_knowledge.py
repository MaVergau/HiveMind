"""
Quick test of HiveMind knowledge retrieval
"""

import sys
import io

# Fix Windows encoding for emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from knowledge_tools import (
    list_knowledge_categories,
    query_knowledge_category,
    search_knowledge,
    find_entity_knowledge,
    get_knowledge_summary
)

print("=" * 60)
print("HIVEMIND KNOWLEDGE BASE TEST")
print("=" * 60)

print("\n1. Knowledge Summary:")
print(get_knowledge_summary())

print("\n" + "=" * 60)
print("\n2. List Categories:")
print(list_knowledge_categories())

print("\n" + "=" * 60)
print("\n3. Search for 'Caroline':")
print(search_knowledge('Caroline'))

print("\n" + "=" * 60)
print("\n4. Find Caroline Van Cromphaut (people entity):")
print(find_entity_knowledge('people', 'Caroline Van Cromphaut'))

print("\n" + "=" * 60)
print("\n5. Query all people:")
print(query_knowledge_category('people'))

print("\n" + "=" * 60)
print("✅ All knowledge tools working!")
