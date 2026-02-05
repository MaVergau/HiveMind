"""
Knowledge System - Time-aware ingestion and semantic organization
Processes raw input files into structured, queryable knowledge with temporal context
"""

import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import re


class TemporalMetadata:
    """Tracks temporal information about knowledge artifacts"""
    
    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.ingestion_time = datetime.now()
        self.file_modified_time = datetime.fromtimestamp(source_file.stat().st_mtime)
        self.extracted_dates = []
        self.temporal_context = None  # e.g., "2025-Q1", "January 2025 meeting"
        
    def to_dict(self) -> Dict:
        return {
            "source_file": str(self.source_file),
            "ingestion_time": self.ingestion_time.isoformat(),
            "file_modified_time": self.file_modified_time.isoformat(),
            "extracted_dates": [d.isoformat() if isinstance(d, datetime) else d for d in self.extracted_dates],
            "temporal_context": self.temporal_context
        }


class KnowledgeArtifact:
    """Represents a single piece of knowledge with metadata and provenance"""
    
    def __init__(
        self,
        content: str,
        category: str,
        source: Path,
        metadata: TemporalMetadata,
        tags: List[str] = None,
        entities: Dict[str, List[str]] = None
    ):
        self.id = self._generate_id(content, source)
        self.content = content
        self.category = category
        self.source = source
        self.metadata = metadata
        self.tags = tags or []
        self.entities = entities or {}  # e.g., {"people": [...], "topics": [...]}
        
    def _generate_id(self, content: str, source: Path) -> str:
        """Generate unique ID based on content and source"""
        hash_input = f"{source.name}:{content[:100]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "source": str(self.source),
            "metadata": self.metadata.to_dict(),
            "tags": self.tags,
            "entities": self.entities
        }


class IngestionPipeline:
    """Processes raw input files into knowledge artifacts"""
    
    def __init__(self, raw_input_dir: Path, knowledge_base_dir: Path):
        self.raw_input_dir = raw_input_dir
        self.knowledge_base_dir = knowledge_base_dir
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create structured directories
        self.categories_dir = knowledge_base_dir / "categories"
        self.temporal_dir = knowledge_base_dir / "temporal"
        self.entities_dir = knowledge_base_dir / "entities"
        self.index_dir = knowledge_base_dir / "indexes"
        
        for dir_path in [self.categories_dir, self.temporal_dir, self.entities_dir, self.index_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def extract_dates(self, content: str) -> List[str]:
        """Extract date references from content"""
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # ISO dates
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            r'\b(?:Q[1-4])\s*\d{4}\b',  # Quarters
            r'\bFY\d{2}\b'  # Fiscal years
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, content, re.IGNORECASE))
        return dates
    
    def extract_entities(self, content: str, source_path: Path) -> Dict[str, List[str]]:
        """Extract named entities from content"""
        entities = {
            "people": [],
            "organizations": [],
            "topics": [],
            "technologies": []
        }
        
        # Extract from filename and path
        category = source_path.parent.name
        
        # Technology keywords
        tech_keywords = ["AI", "Azure", "Microsoft", "Copilot", "M365", "Dynamics", "Cloud", "Security"]
        for tech in tech_keywords:
            if tech.lower() in content.lower():
                entities["technologies"].append(tech)
        
        # People names (basic pattern matching)
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        potential_names = re.findall(name_pattern, content)
        entities["people"] = list(set(potential_names[:10]))  # Limit to first 10 unique
        
        # Organizations
        if "Proximus" in content:
            entities["organizations"].append("Proximus")
        if "Microsoft" in content:
            entities["organizations"].append("Microsoft")
            
        return entities
    
    def categorize_source(self, source_path: Path) -> str:
        """Determine category based on source folder structure"""
        relative_path = source_path.relative_to(self.raw_input_dir)
        parts = relative_path.parts
        
        if len(parts) > 1:
            return parts[0]  # Use first directory as category
        return "uncategorized"
    
    async def ingest_file(self, file_path: Path) -> Optional[KnowledgeArtifact]:
        """Ingest a single file into the knowledge system"""
        
        # Skip non-markdown files for now (can extend later)
        if file_path.suffix not in ['.md', '.txt']:
            print(f"⏭️  Skipping {file_path.name} (unsupported format)")
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Create temporal metadata
            metadata = TemporalMetadata(file_path)
            metadata.extracted_dates = self.extract_dates(content)
            
            # Determine temporal context from dates or filename
            if metadata.extracted_dates:
                metadata.temporal_context = metadata.extracted_dates[0]
            elif "202" in file_path.name:  # Contains year
                year_match = re.search(r'20\d{2}', file_path.name)
                if year_match:
                    metadata.temporal_context = year_match.group()
            
            # Categorize and extract entities
            category = self.categorize_source(file_path)
            entities = self.extract_entities(content, file_path)
            
            # Create knowledge artifact
            artifact = KnowledgeArtifact(
                content=content,
                category=category,
                source=file_path,
                metadata=metadata,
                entities=entities
            )
            
            # Save to knowledge base
            await self.save_artifact(artifact)
            
            print(f"✅ Ingested: {file_path.name} → {category}")
            return artifact
            
        except Exception as e:
            print(f"❌ Error ingesting {file_path.name}: {e}")
            return None
    
    async def save_artifact(self, artifact: KnowledgeArtifact):
        """Save artifact to structured knowledge base"""
        
        # Save by category
        category_file = self.categories_dir / f"{artifact.category}.jsonl"
        with open(category_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(artifact.to_dict()) + '\n')
        
        # Save temporal index
        if artifact.metadata.temporal_context:
            temporal_key = artifact.metadata.temporal_context.replace('/', '-').replace(' ', '_')
            temporal_file = self.temporal_dir / f"{temporal_key}.jsonl"
            with open(temporal_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "artifact_id": artifact.id,
                    "source": str(artifact.source),
                    "category": artifact.category,
                    "temporal_context": artifact.metadata.temporal_context
                }) + '\n')
        
        # Save entity indexes
        for entity_type, entity_list in artifact.entities.items():
            if entity_list:
                entity_file = self.entities_dir / f"{entity_type}.jsonl"
                with open(entity_file, 'a', encoding='utf-8') as f:
                    for entity in entity_list:
                        f.write(json.dumps({
                            "entity": entity,
                            "artifact_id": artifact.id,
                            "category": artifact.category,
                            "source": str(artifact.source)
                        }) + '\n')
    
    async def ingest_all(self):
        """Ingest all files from raw input directory"""
        print(f"\n🔄 Starting ingestion from: {self.raw_input_dir}")
        print(f"📦 Knowledge base: {self.knowledge_base_dir}\n")
        
        markdown_files = list(self.raw_input_dir.rglob('*.md')) + list(self.raw_input_dir.rglob('*.txt'))
        
        if not markdown_files:
            print("⚠️  No markdown/text files found to ingest")
            return
        
        print(f"Found {len(markdown_files)} files to process\n")
        
        artifacts = []
        for file_path in markdown_files:
            artifact = await self.ingest_file(file_path)
            if artifact:
                artifacts.append(artifact)
        
        # Generate master index
        await self.generate_master_index(artifacts)
        
        print(f"\n✨ Ingestion complete: {len(artifacts)} artifacts created")
        print(f"📊 Categories: {len(set(a.category for a in artifacts))}")
        print(f"⏰ Temporal contexts: {len(set(a.metadata.temporal_context for a in artifacts if a.metadata.temporal_context))}")
    
    async def generate_master_index(self, artifacts: List[KnowledgeArtifact]):
        """Generate master index of all artifacts"""
        index_file = self.index_dir / "master_index.json"
        
        index_data = {
            "generated_at": datetime.now().isoformat(),
            "total_artifacts": len(artifacts),
            "categories": {},
            "temporal_contexts": {},
            "entity_types": {}
        }
        
        # Build category index
        for artifact in artifacts:
            if artifact.category not in index_data["categories"]:
                index_data["categories"][artifact.category] = []
            index_data["categories"][artifact.category].append(artifact.id)
            
            # Build temporal index
            if artifact.metadata.temporal_context:
                ctx = artifact.metadata.temporal_context
                if ctx not in index_data["temporal_contexts"]:
                    index_data["temporal_contexts"][ctx] = []
                index_data["temporal_contexts"][ctx].append(artifact.id)
            
            # Build entity type index
            for entity_type, entities in artifact.entities.items():
                if entities:
                    if entity_type not in index_data["entity_types"]:
                        index_data["entity_types"][entity_type] = set()
                    index_data["entity_types"][entity_type].update(entities)
        
        # Convert sets to lists for JSON serialization
        for entity_type in index_data["entity_types"]:
            index_data["entity_types"][entity_type] = list(index_data["entity_types"][entity_type])
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        
        print(f"\n📇 Master index created: {index_file}")


async def main():
    """Main entry point for knowledge system ingestion"""
    raw_input = Path("RawInput")
    knowledge_base = Path("knowledge_base")
    
    pipeline = IngestionPipeline(raw_input, knowledge_base)
    await pipeline.ingest_all()


if __name__ == "__main__":
    asyncio.run(main())
