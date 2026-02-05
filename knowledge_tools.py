"""
Knowledge System Tools - Integration with HiveMind Agent
Provides tools for querying and managing the time-aware knowledge base
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class KnowledgeQuery:
    """Query interface for the knowledge base"""
    
    def __init__(self, knowledge_base_dir: Path = Path("knowledge_base")):
        self.kb_dir = knowledge_base_dir
        self.categories_dir = self.kb_dir / "categories"
        self.temporal_dir = self.kb_dir / "temporal"
        self.entities_dir = self.kb_dir / "entities"
        self.index_dir = self.kb_dir / "indexes"
    
    def query_by_category(self, category: str) -> List[Dict]:
        """Retrieve all artifacts from a specific category"""
        category_file = self.categories_dir / f"{category}.jsonl"
        
        if not category_file.exists():
            return []
        
        artifacts = []
        with open(category_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    artifacts.append(json.loads(line))
        
        return artifacts
    
    def query_by_temporal_context(self, temporal_context: str) -> List[Dict]:
        """Retrieve artifacts from a specific time period"""
        temporal_key = temporal_context.replace('/', '-').replace(' ', '_')
        temporal_file = self.temporal_dir / f"{temporal_key}.jsonl"
        
        if not temporal_file.exists():
            return []
        
        refs = []
        with open(temporal_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    refs.append(json.loads(line))
        
        return refs
    
    def query_by_entity(self, entity_type: str, entity_name: str) -> List[Dict]:
        """Find artifacts mentioning a specific entity"""
        entity_file = self.entities_dir / f"{entity_type}.jsonl"
        
        if not entity_file.exists():
            return []
        
        matches = []
        with open(entity_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entity_name.lower() in entry.get("entity", "").lower():
                        matches.append(entry)
        
        return matches
    
    def get_master_index(self) -> Dict:
        """Get the master index of the knowledge base"""
        index_file = self.index_dir / "master_index.json"
        
        if not index_file.exists():
            return {}
        
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def search_content(self, query: str, category: str = None) -> List[Dict]:
        """Search for text across artifacts"""
        results = []
        
        # Determine which categories to search
        if category:
            categories_to_search = [category]
        else:
            categories_to_search = [f.stem for f in self.categories_dir.glob("*.jsonl")]
        
        for cat in categories_to_search:
            artifacts = self.query_by_category(cat)
            for artifact in artifacts:
                if query.lower() in artifact.get("content", "").lower():
                    results.append(artifact)
        
        return results


# Tool functions for HiveMind agent

def list_knowledge_categories() -> str:
    """List all available knowledge categories in the knowledge base."""
    kb = KnowledgeQuery()
    index = kb.get_master_index()
    
    if not index or not index.get("categories"):
        return "Knowledge base is empty. Run ingestion first with: python knowledge_system.py"
    
    categories = index["categories"]
    output = [f"📚 Knowledge Base Categories ({len(categories)} total):\n"]
    
    for category, artifact_ids in sorted(categories.items()):
        output.append(f"  • {category}: {len(artifact_ids)} artifacts")
    
    return "\n".join(output)


def query_knowledge_category(category: str) -> str:
    """Query all knowledge artifacts from a specific category.
    
    Args:
        category: Name of the category to query (e.g., 'LinkedIn', 'Meeting transcripts')
    """
    kb = KnowledgeQuery()
    artifacts = kb.query_by_category(category)
    
    if not artifacts:
        return f"No artifacts found in category '{category}'"
    
    output = [f"📁 Category: {category} ({len(artifacts)} artifacts)\n"]
    
    for i, artifact in enumerate(artifacts[:5], 1):  # Show first 5
        source = Path(artifact["source"]).name
        snippet = artifact["content"][:200].replace('\n', ' ')
        output.append(f"{i}. {source}")
        output.append(f"   {snippet}...")
        output.append("")
    
    if len(artifacts) > 5:
        output.append(f"   ... and {len(artifacts) - 5} more")
    
    return "\n".join(output)


def query_temporal_knowledge(time_period: str) -> str:
    """Query knowledge from a specific time period.
    
    Args:
        time_period: Time period to query (e.g., '2024', 'Q1 2025', 'January 2025')
    """
    kb = KnowledgeQuery()
    refs = kb.query_by_temporal_context(time_period)
    
    if not refs:
        return f"No knowledge found for time period '{time_period}'"
    
    output = [f"⏰ Time Period: {time_period} ({len(refs)} artifacts)\n"]
    
    for i, ref in enumerate(refs[:10], 1):
        source = Path(ref["source"]).name
        category = ref["category"]
        output.append(f"{i}. [{category}] {source}")
    
    if len(refs) > 10:
        output.append(f"\n   ... and {len(refs) - 10} more")
    
    return "\n".join(output)


def search_knowledge(query: str, category: str = None) -> str:
    """Search for specific content across the knowledge base.
    
    Args:
        query: Text to search for
        category: Optional category to limit search to
    """
    kb = KnowledgeQuery()
    results = kb.search_content(query, category)
    
    if not results:
        return f"No results found for '{query}'"
    
    output = [f"🔍 Search: '{query}' ({len(results)} matches)\n"]
    
    for i, artifact in enumerate(results[:5], 1):
        source = Path(artifact["source"]).name
        cat = artifact["category"]
        
        # Find the matching context
        content = artifact["content"].lower()
        idx = content.find(query.lower())
        if idx != -1:
            start = max(0, idx - 50)
            end = min(len(content), idx + len(query) + 50)
            context = artifact["content"][start:end].replace('\n', ' ')
            output.append(f"{i}. [{cat}] {source}")
            output.append(f"   ...{context}...")
            output.append("")
    
    if len(results) > 5:
        output.append(f"   ... and {len(results) - 5} more matches")
    
    return "\n".join(output)


def find_entity_knowledge(entity_type: str, entity_name: str) -> str:
    """Find knowledge related to a specific entity (person, organization, technology, topic).
    
    Args:
        entity_type: Type of entity ('people', 'organizations', 'technologies', 'topics')
        entity_name: Name of the entity to search for
    """
    kb = KnowledgeQuery()
    matches = kb.query_by_entity(entity_type, entity_name)
    
    if not matches:
        return f"No knowledge found for {entity_type} entity '{entity_name}'"
    
    output = [f"👤 Entity: {entity_name} ({entity_type}) - {len(matches)} mentions\n"]
    
    for i, match in enumerate(matches[:10], 1):
        source = Path(match["source"]).name
        category = match["category"]
        output.append(f"{i}. [{category}] {source}")
    
    if len(matches) > 10:
        output.append(f"\n   ... and {len(matches) - 10} more")
    
    return "\n".join(output)


def get_knowledge_summary() -> str:
    """Get a summary of the entire knowledge base."""
    kb = KnowledgeQuery()
    index = kb.get_master_index()
    
    if not index:
        return "Knowledge base is empty. Run ingestion first with: python knowledge_system.py"
    
    output = ["📊 Knowledge Base Summary\n"]
    output.append(f"Generated: {index.get('generated_at', 'Unknown')}")
    output.append(f"Total Artifacts: {index.get('total_artifacts', 0)}\n")
    
    # Categories
    categories = index.get("categories", {})
    output.append(f"📁 Categories ({len(categories)}):")
    for cat, artifacts in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        output.append(f"  • {cat}: {len(artifacts)} artifacts")
    
    # Temporal contexts
    temporal = index.get("temporal_contexts", {})
    if temporal:
        output.append(f"\n⏰ Time Periods ({len(temporal)}):")
        for period in sorted(temporal.keys())[:5]:
            output.append(f"  • {period}: {len(temporal[period])} artifacts")
    
    # Entity types
    entities = index.get("entity_types", {})
    if entities:
        output.append(f"\n🏷️  Entity Types:")
        for etype, elist in entities.items():
            output.append(f"  • {etype}: {len(elist)} unique entities")
    
    return "\n".join(output)
