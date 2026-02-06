"""
Knowledge System Tools - Integration with HiveMind Agent
Provides tools for querying and managing the time-aware knowledge base
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class KnowledgeQuery:
    """Query interface for the markdown-based knowledge base"""
    
    def __init__(self, knowledge_base_dir: Path = Path("markdown_files")):
        self.kb_dir = knowledge_base_dir
        self.entities_dir = self.kb_dir / "entities"
        self.events_dir = self.kb_dir / "events"
        self.temporal_dir = self.kb_dir / "temporal"
    
    def parse_markdown_frontmatter(self, file_path: Path) -> Dict[str, Any]:
        """Parse YAML frontmatter and content from markdown file"""
        content = file_path.read_text(encoding='utf-8')
        
        # Extract YAML frontmatter
        frontmatter = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                yaml_content = parts[1].strip()
                for line in yaml_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip()
                
                # Content is after second ---
                body = parts[2].strip()
            else:
                body = content
        else:
            body = content
        
        return {
            'frontmatter': frontmatter,
            'content': body,
            'file_path': str(file_path)
        }
    
    def query_by_category(self, category: str) -> List[Dict]:
        """Retrieve all artifacts from a specific category"""
        category_map = {
            'people': self.entities_dir / 'people',
            'organizations': self.entities_dir / 'organizations',
            'technologies': self.entities_dir / 'technologies',
            'topics': self.entities_dir / 'topics',
            'meetings': self.events_dir / 'meetings',
            'decisions': self.events_dir / 'decisions',
            'milestones': self.events_dir / 'milestones'
        }
        
        category_dir = category_map.get(category.lower())
        if not category_dir or not category_dir.exists():
            return []
        
        artifacts = []
        for md_file in category_dir.glob('*.md'):
            if md_file.name == 'TEMPLATE.md':
                continue
            parsed = self.parse_markdown_frontmatter(md_file)
            artifacts.append({
                'category': category,
                'source': str(md_file),
                'name': parsed['frontmatter'].get('name', md_file.stem),
                'type': parsed['frontmatter'].get('type', category),
                'frontmatter': parsed['frontmatter'],
                'content': parsed['content']
            })
        
        return artifacts
    
    def query_by_temporal_context(self, temporal_context: str) -> List[Dict]:
        """Retrieve artifacts from a specific time period"""
        # For now, search through meetings and events for temporal references
        results = []
        
        meetings = self.query_by_category('meetings')
        for meeting in meetings:
            date = meeting['frontmatter'].get('date', '')
            if temporal_context.lower() in date.lower():
                results.append(meeting)
        
        return results
    
    def query_by_entity(self, entity_type: str, entity_name: str) -> List[Dict]:
        """Find artifacts mentioning a specific entity"""
        matches = self.query_by_category(entity_type)
        
        # Filter by name
        filtered = []
        for match in matches:
            name = match.get('name', '').lower()
            if entity_name.lower() in name:
                filtered.append(match)
        
        return filtered
    
    def get_master_index(self) -> Dict:
        """Get summary statistics of the knowledge base"""
        stats = {
            'generated_at': datetime.now().isoformat(),
            'categories': {},
            'total_artifacts': 0
        }
        
        # Count entities
        for entity_type in ['people', 'organizations', 'technologies', 'topics']:
            artifacts = self.query_by_category(entity_type)
            stats['categories'][entity_type] = [a['name'] for a in artifacts]
            stats['total_artifacts'] += len(artifacts)
        
        # Count events
        for event_type in ['meetings', 'decisions', 'milestones']:
            artifacts = self.query_by_category(event_type)
            stats['categories'][event_type] = [a['name'] for a in artifacts]
            stats['total_artifacts'] += len(artifacts)
        
        return stats
    
    def search_content(self, query: str, category: str = None) -> List[Dict]:
        """Search for text across artifacts"""
        results = []
        
        # Determine which categories to search
        if category:
            categories_to_search = [category]
        else:
            categories_to_search = ['people', 'organizations', 'technologies', 'topics', 'meetings']
        
        for cat in categories_to_search:
            artifacts = self.query_by_category(cat)
            for artifact in artifacts:
                # Search in both name and content
                name = artifact.get('name', '').lower()
                content = artifact.get('content', '').lower()
                
                if query.lower() in name or query.lower() in content:
                    results.append(artifact)
        
        return results


# Tool functions for HiveMind agent

def list_knowledge_categories() -> str:
    """List all available knowledge categories in the knowledge base."""
    kb = KnowledgeQuery()
    index = kb.get_master_index()
    
    if not index or not index.get("categories"):
        return "Knowledge base is empty or not found."
    
    categories = index["categories"]
    output = [f"📚 Knowledge Base Categories ({len(categories)} total):\n"]
    
    for category, items in sorted(categories.items()):
        output.append(f"  • {category}: {len(items)} items")
    
    return "\n".join(output)


def query_knowledge_category(category: str) -> str:
    """Query all knowledge artifacts from a specific category.
    
    Args:
        category: Name of the category to query (e.g., 'people', 'organizations', 'technologies', 'meetings')
    """
    kb = KnowledgeQuery()
    artifacts = kb.query_by_category(category)
    
    if not artifacts:
        return f"No items found in category '{category}'. Available categories: people, organizations, technologies, topics, meetings"
    
    output = [f"📁 Category: {category} ({len(artifacts)} items)\n"]
    
    for i, artifact in enumerate(artifacts[:10], 1):  # Show first 10
        name = artifact.get('name', 'Unknown')
        
        # Add key details based on type
        if category == 'people':
            role = artifact['frontmatter'].get('role', 'Unknown Role')
            org = artifact['frontmatter'].get('organization', 'Unknown Org')
            output.append(f"{i}. **{name}** - {role} at {org}")
        elif category == 'meetings':
            date = artifact['frontmatter'].get('date', 'Unknown Date')
            output.append(f"{i}. **{name}** ({date})")
        else:
            output.append(f"{i}. **{name}**")
    
    if len(artifacts) > 10:
        output.append(f"\n   ... and {len(artifacts) - 10} more")
    
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
        name = artifact.get('name', 'Unknown')
        cat = artifact.get('category', 'unknown')
        
        # Show relevant excerpt
        content = artifact.get('content', '')
        if len(content) > 200:
            content = content[:200] + "..."
        
        output.append(f"{i}. [{cat}] **{name}**")
        if category != 'people':  # Don't show content snippet for people (show in frontmatter instead)
            output.append(f"   {content.replace(chr(10), ' ')}")
        else:
            role = artifact['frontmatter'].get('role', 'Unknown Role')
            org = artifact['frontmatter'].get('organization', 'Unknown')
            output.append(f"   {role} at {org}")
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
        # Try searching across all content
        all_matches = kb.search_content(entity_name)
        if all_matches:
            return f"No direct {entity_type} entity found, but '{entity_name}' is mentioned in {len(all_matches)} items. Use search_knowledge for details."
        return f"No knowledge found for {entity_type} entity '{entity_name}'"
    
    output = [f"👤 Entity: {entity_name} ({entity_type})\n"]
    
    for match in matches:
        name = match.get('name', 'Unknown')
        output.append(f"**{name}**")
        
        # Show key details based on entity type
        if entity_type == 'people':
            role = match['frontmatter'].get('role', 'Unknown')
            org = match['frontmatter'].get('organization', 'Unknown')
            location = match['frontmatter'].get('location', 'Unknown')
            output.append(f"  Role: {role}")
            output.append(f"  Organization: {org}")
            output.append(f"  Location: {location}")
            
            # Show expertise
            content = match.get('content', '')
            if '## Expertise' in content:
                expertise_section = content.split('## Expertise')[1].split('##')[0].strip()
                output.append(f"  Expertise: {expertise_section[:200]}...")
        
        elif entity_type == 'organizations':
            output.append(f"  Type: {match['frontmatter'].get('tags', 'Unknown')}")
        
        elif entity_type == 'technologies':
            output.append(f"  Category: {match['frontmatter'].get('category', 'Unknown')}")
        
        output.append("")
    
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

def find_relationships(entity_name: str, relationship_type: str = None) -> str:
    """Find relationships for a specific entity.
    
    Args:
        entity_name: Name of the entity to find relationships for
        relationship_type: Optional filter for specific relationship type (works_for, uses, attended, etc.)
    """
    kb = KnowledgeQuery()
    relationships = []
    
    # Search for entity across all categories
    for category in ['people', 'organizations', 'technologies', 'topics', 'meetings']:
        artifacts = kb.query_by_category(category)
        for artifact in artifacts:
            name = artifact.get('name', '').lower()
            if entity_name.lower() in name:
                # Check frontmatter for relationships
                frontmatter = artifact.get('frontmatter', {})
                if 'relationships' in str(frontmatter):
                    # Parse relationships from frontmatter
                    for key, value in frontmatter.items():
                        if key in ['works_for', 'employs', 'uses_technologies', 'attended', 'discussed_in']:
                            if not relationship_type or key == relationship_type:
                                relationships.append({
                                    'entity': artifact.get('name'),
                                    'type': key,
                                    'target': value
                                })
    
    if not relationships:
        return f"No relationships found for '{entity_name}'"
    
    output = [f"🔗 Relationships for '{entity_name}':\n"]
    for rel in relationships:
        output.append(f"  • {rel['type']}: {rel['target']}")
    
    return "\n".join(output)


def get_entity_network(entity_name: str, depth: int = 1) -> str:
    """Get the network of entities connected to the given entity.
    
    Args:
        entity_name: Name of the entity
        depth: How many levels deep to traverse (1 = direct connections, 2 = connections of connections)
    """
    kb = KnowledgeQuery()
    network = {entity_name: []}
    
    # Find direct relationships
    for category in ['people', 'organizations', 'technologies', 'topics', 'meetings']:
        artifacts = kb.query_by_category(category)
        for artifact in artifacts:
            name = artifact.get('name', '').lower()
            if entity_name.lower() in name:
                frontmatter = artifact.get('frontmatter', {})
                # Extract all relationship values
                for key, value in frontmatter.items():
                    if key in ['works_for', 'organization', 'employs', 'uses_technologies', 'attended']:
                        if isinstance(value, list):
                            network[entity_name].extend(value)
                        else:
                            network[entity_name].append(value)
    
    if not network[entity_name]:
        return f"No connections found for '{entity_name}'"
    
    output = [f"🕸️  Entity Network for '{entity_name}':\n"]
    output.append(f"Direct Connections ({len(network[entity_name])}):")
    for conn in set(network[entity_name]):
        output.append(f"  • {conn}")
    
    return "\n".join(output)