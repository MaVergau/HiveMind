"""
AI-Powered HiveMind Knowledge Builder
Uses Azure OpenAI GPT-4 to intelligently extract entities from documents
"""

import os
import sys
import io
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

# Fix Windows encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

# For PDF extraction
try:
    import pypdf
except ImportError:
    pypdf = None

# For document conversion (DOCX, PDF, etc.)
try:
    from markitdown import MarkItDown
    markitdown_converter = MarkItDown()
except ImportError:
    markitdown_converter = None

# Load environment
load_dotenv()


class AIKnowledgeBuilder:
    def __init__(self):
        self.base_path = Path("markdown_files")
        self.raw_input = Path("RawInput")
        
        # Initialize Azure OpenAI client
        # Using the direct cognitive services endpoint you provided
        self.client = AzureOpenAI(
            azure_endpoint="https://grippy-resource.cognitiveservices.azure.com/",
            api_version="2024-05-01-preview",
            azure_ad_token_provider=get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
        )
        
        # Storage
        self.extracted_entities = {
            'people': [],
            'organizations': [],
            'technologies': [],
            'topics': [],
            'meetings': [],
            'relationships': []
        }
        
        self.stats = defaultdict(int)
    
    def resolve_attendees(self):
        """Resolve meeting attendee first names to full names from known people"""
        # Build lookup of first names to full names
        first_name_map = {}
        for person in self.extracted_entities['people']:
            full_name = person.get('name', '')
            if full_name:
                first_name = full_name.split()[0]
                first_name_map[first_name.lower()] = full_name
        
        # Resolve attendees in meetings
        for meeting in self.extracted_entities['meetings']:
            attendees = meeting.get('attendees', [])
            resolved = []
            
            for attendee in attendees:
                attendee_clean = attendee.strip()
                # Check if it's already a full name (has space)
                if ' ' in attendee_clean:
                    resolved.append(attendee_clean)
                else:
                    # Try to resolve first name
                    first_name_key = attendee_clean.lower()
                    if first_name_key in first_name_map:
                        resolved.append(first_name_map[first_name_key])
                    else:
                        resolved.append(attendee_clean)  # Keep original if unknown
            
            meeting['attendees_resolved'] = resolved
    
    def consolidate_technologies(self) -> List[str]:
        """Use GPT-4 to consolidate and deduplicate technology names"""
        if not self.extracted_entities['technologies']:
            return []
        
        # Get unique tech list
        tech_list = list(set(self.extracted_entities['technologies']))
        
        # If too many, use GPT-4 to consolidate
        if len(tech_list) > 50:
            print(f"  🤖 Consolidating {len(tech_list)} technologies with GPT-4...")
            
            system_prompt = """You are a technology taxonomy expert. Consolidate this list of technologies:
1. Merge obvious duplicates (e.g., 'M365' = 'Microsoft 365')
2. Fix typos (e.g., 'Enter ID' → 'Entra ID')
3. Keep major products, consolidate minor variants
4. Use canonical product names

Return ONLY a JSON array of consolidated technology names."""
            
            user_prompt = f"""Consolidate these technologies:
{json.dumps(tech_list, indent=2)}

Return JSON array of canonical names only."""
            
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Remove markdown code blocks if present
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                
                consolidated = json.loads(result_text)
                print(f"  ✓ Consolidated: {len(tech_list)} → {len(consolidated)} technologies")
                self.stats['ai_extractions'] += 1
                return consolidated
                
            except Exception as e:
                print(f"  ⚠️ Consolidation failed: {e}, using manual normalization")
                return tech_list
        else:
            return tech_list
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF file using markitdown or pypdf"""
        # Try markitdown first for better extraction
        if markitdown_converter:
            try:
                result = markitdown_converter.convert(str(pdf_path))
                text = result.text_content if hasattr(result, 'text_content') else str(result)
                self.stats['pdf_processed'] += 1
                return text[:15000]  # Limit text length
            except Exception as e:
                print(f"  ⚠️ Markitdown error for {pdf_path.name}: {e}, trying pypdf...")
        
        # Fallback to pypdf
        if pypdf is None:
            self.stats['pdf_skipped'] += 1
            return ""
        
        try:
            reader = pypdf.PdfReader(pdf_path)
            text = ""
            for page in reader.pages[:10]:  # Limit to first 10 pages
                text += page.extract_text() + "\n"
            self.stats['pdf_processed'] += 1
            return text[:15000]  # Limit text length
        except Exception as e:
            print(f"  ⚠️ Error reading PDF {pdf_path.name}: {e}")
            self.stats['pdf_errors'] += 1
            return ""
    
    def extract_text_from_docx(self, docx_path: Path) -> str:
        """Extract text from DOCX file using markitdown"""
        if markitdown_converter is None:
            self.stats['docx_skipped'] += 1
            print(f"  ⚠️ markitdown not installed - install with: pip install markitdown")
            return ""
        
        try:
            result = markitdown_converter.convert(str(docx_path))
            text = result.text_content if hasattr(result, 'text_content') else str(result)
            self.stats['docx_processed'] += 1
            return text
        except Exception as e:
            print(f"  ⚠️ Error reading DOCX {docx_path.name}: {e}")
            self.stats['docx_errors'] += 1
            return ""
    
    def extract_entities_with_ai(self, text: str, source_file: str, document_type: str) -> Dict:
        """Use GPT-4 to extract structured entities from text"""
        
        system_prompt = """You are an expert knowledge extraction AI for the HiveMind system.
Extract structured entities AND their relationships following the HiveMind ontology. Return JSON only, no markdown formatting.

ENTITY TYPES (HiveMind Ontology v2.0):

1. PERSON - Individuals from LinkedIn profiles, meeting attendees, decision makers
   - Extract: Full name, current role, company, location (city/country), key expertise areas
   - Include: Only people with verifiable roles or context
   - Exclude: Generic mentions, section headers, template text

2. ORGANIZATION - Companies, institutions, partners, customers
   - Extract: Full organization name (official name)
   - Include: Employers, partners, vendors, customers, competitors
   - Exclude: Generic terms like "the company", "our organization"

3. TECHNOLOGY - Products, platforms, tools, technical solutions
   - Extract: Specific technology names (Azure, Copilot, Databricks, etc.)
   - Include: Cloud platforms, AI/ML tools, development tools, SaaS products
   - Exclude: Generic terms like "cloud", "AI" without specific product names

4. TOPIC - Themes, initiatives, strategic areas, RAIN roles
   - Extract: Strategic initiatives, business processes, technical domains
   - Include: Project names, transformation initiatives, role descriptions
   - Limit: 3-7 most significant topics per document

5. MEETING - Events with attendees and discussions
   - Extract: Title, date (ISO format YYYY-MM-DD or quarter "Q4 2025"), attendees (full names), main topics
   - Include: Formal meetings, discussions, planning sessions
   - Date: Parse from text or use "Unknown" if not found

RELATIONSHIP EXTRACTION:
Identify relationships between entities:
- works_for: Person works at Organization
- attended: Person attended Meeting
- uses: Organization uses Technology
- discussed_in: Topic/Technology discussed in Meeting
- mentioned_with: Entities mentioned together (co-occurrence)

EXTRACTION GUIDELINES:
- Be precise: Use exact names as they appear
- Be selective: Quality over quantity (avoid noise)
- Be consistent: Follow naming conventions (proper capitalization)
- Provide context: Include roles with people, categories with technologies
- Extract relationships: Identify how entities relate to each other

Return in this exact JSON format:
{
  "people": [{"name": "Full Name", "role": "Job Title", "company": "Company Name", "location": "City, Country", "skills": ["skill1", "skill2"]}],
  "organizations": ["Official Organization Name"],
  "technologies": ["Specific Technology Name"],
  "topics": ["Strategic Topic or Initiative"],
  "meetings": [{"title": "Meeting Name", "date": "YYYY-MM-DD or Q4 2025", "attendees": ["Full Name1", "Full Name2"], "topics": ["topic1"]}],
  "relationships": [
    {"type": "works_for", "source": "Person Name", "target": "Organization Name"},
    {"type": "uses", "source": "Organization Name", "target": "Technology Name"},
    {"type": "attended", "source": "Person Name", "target": "Meeting Title"},
    {"type": "discussed_in", "source": "Technology/Topic", "target": "Meeting Title"}
  ]
}

Only include entities and relationships that are clearly mentioned and relevant. Use empty arrays if not applicable."""

        user_prompt = f"""Document Type: {document_type}
Source: {source_file}

Document Content:
{text[:8000]}

Extract all relevant entities following the HiveMind ontology."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1",  # Your deployment name
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            entities = json.loads(result_text)
            self.stats['ai_extractions'] += 1
            
            # Store relationships
            if 'relationships' in entities:
                self.extracted_entities['relationships'].extend(entities.get('relationships', []))
            
            # Log what was extracted
            extracted_summary = []
            if entities.get('people'): extracted_summary.append(f"{len(entities['people'])} people")
            if entities.get('organizations'): extracted_summary.append(f"{len(entities['organizations'])} orgs")
            if entities.get('technologies'): extracted_summary.append(f"{len(entities['technologies'])} tech")
            if entities.get('topics'): extracted_summary.append(f"{len(entities['topics'])} topics")
            if entities.get('meetings'): extracted_summary.append(f"{len(entities['meetings'])} meetings")
            if entities.get('relationships'): extracted_summary.append(f"{len(entities['relationships'])} relationships")
            
            if extracted_summary:
                print(f"      ✓ Extracted: {', '.join(extracted_summary)}")
            
            return entities
            
        except Exception as e:
            print(f"  ⚠️ AI extraction error: {e}")
            self.stats['ai_errors'] += 1
            return {'people': [], 'organizations': [], 'technologies': [], 'topics': [], 'meetings': []}
    
    def process_linkedin_profile(self, file_path: Path):
        """Process LinkedIn profile with AI"""
        content = file_path.read_text(encoding='utf-8')
        
        print(f"\n    🤖 Analyzing with GPT-4: {file_path.name}")
        entities = self.extract_entities_with_ai(content, str(file_path), "LinkedIn Profile")
        
        # Store extracted people
        for person in entities.get('people', []):
            person['source'] = str(file_path)
            person['type'] = 'linkedin-profile'
            self.extracted_entities['people'].append(person)
            print(f"      👤 {person.get('name', 'Unknown')} - {person.get('role', 'Unknown Role')}")
        
        # Store other entities
        self.extracted_entities['organizations'].extend(entities.get('organizations', []))
        self.extracted_entities['technologies'].extend(entities.get('technologies', []))
    
    def process_meeting_notes(self, file_path: Path):
        """Process meeting notes with AI"""
        content = file_path.read_text(encoding='utf-8')
        
        print(f"\n    🤖 Analyzing with GPT-4: {file_path.name}")
        entities = self.extract_entities_with_ai(content, str(file_path), "Meeting Notes")
        
        # Store meetings
        for meeting in entities.get('meetings', []):
            meeting['source'] = str(file_path)
            self.extracted_entities['meetings'].append(meeting)
            print(f"      📅 {meeting.get('title', 'Meeting')} ({meeting.get('date', 'Unknown date')})")
        
        # Store topics and technologies
        self.extracted_entities['topics'].extend(entities.get('topics', []))
        self.extracted_entities['technologies'].extend(entities.get('technologies', []))
    
    def process_pdf_document(self, file_path: Path):
        """Process PDF with AI"""
        text = self.extract_text_from_pdf(file_path)
        if not text:
            return
        
        print(f"\n    🤖 Analyzing with GPT-4: {file_path.name}")
        print(f"      📄 Extracted {len(text)} characters from PDF")
        
        # Determine document type
        if 'annual report' in file_path.name.lower():
            doc_type = "Annual Report"
        elif 'plan' in file_path.name.lower():
            doc_type = "Strategic Plan"
        else:
            doc_type = "Technical Document"
        
        entities = self.extract_entities_with_ai(text, str(file_path), doc_type)
        
        # Store entities
        self.extracted_entities['organizations'].extend(entities.get('organizations', []))
        self.extracted_entities['technologies'].extend(entities.get('technologies', []))
        self.extracted_entities['topics'].extend(entities.get('topics', []))
    
    def process_docx_document(self, file_path: Path):
        """Process DOCX with AI"""
        print(f"\n    🤖 Analyzing with GPT-4: {file_path.name}")
        text = self.extract_text_from_docx(file_path)
        if not text or len(text) < 50:  # Skip if extraction failed or too short
            print(f"      ⚠️ Skipped: Insufficient content")
            return
        
        print(f"      📄 Extracted {len(text)} characters from DOCX")
        
        # Determine document type
        if 'meeting' in file_path.name.lower() or 'transcript' in file_path.name.lower():
            doc_type = "Meeting Transcript"
            entities = self.extract_entities_with_ai(text, str(file_path), doc_type)
            
            # Store meetings
            for meeting in entities.get('meetings', []):
                meeting['source'] = str(file_path)
                self.extracted_entities['meetings'].append(meeting)
            
            # Store topics and technologies
            self.extracted_entities['topics'].extend(entities.get('topics', []))
            self.extracted_entities['technologies'].extend(entities.get('technologies', []))
            
        elif 'decision' in file_path.name.lower() or 'key' in file_path.name.lower():
            doc_type = "Decision Makers List"
            entities = self.extract_entities_with_ai(text, str(file_path), doc_type)
            
            # Store people as mentioned (not as full profiles)
            # Store organizations and technologies
            self.extracted_entities['organizations'].extend(entities.get('organizations', []))
            self.extracted_entities['technologies'].extend(entities.get('technologies', []))
        
        else:
            doc_type = "Document"
            entities = self.extract_entities_with_ai(text, str(file_path), doc_type)
            
            # Store all entities
            self.extracted_entities['organizations'].extend(entities.get('organizations', []))
            self.extracted_entities['technologies'].extend(entities.get('technologies', []))
            self.extracted_entities['topics'].extend(entities.get('topics', []))
    
    def normalize_name(self, name: str) -> str:
        """Convert name to filename-safe format"""
        import re
        return re.sub(r'[^\w\s-]', '', name.lower()).replace(' ', '-').strip('-')
    
    def normalize_tech_name(self, name: str) -> str:
        """Normalize technology names to consolidate duplicates"""
        # Common normalization rules
        replacements = {
            'M365': 'Microsoft 365',
            'Enter ID': 'Entra ID',
            'Windows 65': 'Windows 365',
            'Copilot Chat': 'Microsoft Copilot',
            'M365 Copilot': 'Microsoft Copilot',
            'Azure AI Studio': 'Azure AI',
            'Azure Machine Learning Workspace': 'Azure Machine Learning',
        }
        return replacements.get(name, name)
    
    def generate_person_file(self, person_data: Dict):
        """Generate person entity file"""
        name = person_data['name']
        normalized_name = self.normalize_name(name)
        file_path = self.base_path / "entities" / "people" / f"{normalized_name}.md"
        
        # Find relationships for this person
        person_relationships = {
            'works_for': [],
            'attended': [],
            'mentioned_with': []
        }
        for rel in self.extracted_entities['relationships']:
            if rel.get('source', '').lower() == name.lower():
                rel_type = rel.get('type', '')
                if rel_type in person_relationships:
                    person_relationships[rel_type].append(rel.get('target', ''))
        
        skills_text = "\n".join([f"- {skill}" for skill in person_data.get('skills', [])])
        
        # Add relationships to frontmatter
        relationships_yaml = ""
        if any(person_relationships.values()):
            relationships_yaml = "relationships:\n"
            if person_relationships['works_for']:
                relationships_yaml += f"  works_for: {person_relationships['works_for'][0]}\n"
            if person_relationships['attended']:
                relationships_yaml += f"  attended: {person_relationships['attended']}\n"
        
        content = f"""---
type: person
name: {name}
role: {person_data.get('role', 'Unknown')}
organization: {person_data.get('company', 'Unknown')}
location: {person_data.get('location', 'Unknown')}
tags: [linkedin-profile, {self.normalize_name(person_data.get('company', ''))}]
{relationships_yaml}source: {person_data.get('source', '')}
created: {datetime.now().strftime('%Y-%m-%d')}
---

# {name}

**{person_data.get('role', 'Unknown')}** at **{person_data.get('company', 'Unknown')}**

## Contact Information
- Location: {person_data.get('location', 'Unknown')}

## Expertise
{skills_text}

## Connections
- Organization: [[{self.normalize_name(person_data.get('company', ''))}|{person_data.get('company', '')}]]
"""
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        self.stats['people_generated'] += 1
    
    def generate_organization_file(self, org_name: str):
        """Generate organization entity file"""
        normalized_name = self.normalize_name(org_name)
        file_path = self.base_path / "entities" / "organizations" / f"{normalized_name}.md"
        
        # Find people from this org
        people_links = []
        for person in self.extracted_entities['people']:
            if person.get('company', '').lower() == org_name.lower():
                people_links.append(f"- [[{self.normalize_name(person['name'])}|{person['name']}]]")
        
        # Find technologies used by this org
        org_technologies = []
        for rel in self.extracted_entities['relationships']:
            if rel.get('type') == 'uses' and rel.get('source', '').lower() == org_name.lower():
                org_technologies.append(rel.get('target', ''))
        
        people_section = "\n".join(people_links) if people_links else "- (None listed)"
        
        # Add relationships to frontmatter
        relationships_yaml = ""
        if people_links or org_technologies:
            relationships_yaml = "relationships:\n"
            if people_links:
                employee_names = [p.get('name') for p in self.extracted_entities['people'] if p.get('company', '').lower() == org_name.lower()]
                relationships_yaml += f"  employs: {employee_names}\n"
            if org_technologies:
                relationships_yaml += f"  uses_technologies: {org_technologies}\n"
        
        content = f"""---
type: organization
name: {org_name}
tags: [organization]
{relationships_yaml}created: {datetime.now().strftime('%Y-%m-%d')}
---

# {org_name}

## Overview
{org_name} organization in the HiveMind knowledge base.

## People
{people_section}

## Technologies
"""
        
        # Add technology links
        unique_techs = set(self.extracted_entities['technologies'])
        for tech in sorted(unique_techs):
            content += f"- [[{self.normalize_name(tech)}|{tech}]]\n"
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        self.stats['orgs_generated'] += 1
    
    def generate_technology_file(self, tech_name: str):
        """Generate technology entity file"""
        normalized_name = self.normalize_name(tech_name)
        file_path = self.base_path / "entities" / "technologies" / f"{normalized_name}.md"
        
        content = f"""---
type: technology
name: {tech_name}
tags: [technology]
created: {datetime.now().strftime('%Y-%m-%d')}
---

# {tech_name}

## Overview
{tech_name} technology referenced in HiveMind knowledge base.

## Related People
"""
        
        # Link to people with this skill
        for person in self.extracted_entities['people']:
            skills = person.get('skills', [])
            if any(tech_name.lower() in skill.lower() for skill in skills):
                content += f"- [[{self.normalize_name(person['name'])}|{person['name']}]]\n"
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        self.stats['tech_generated'] += 1
    
    def generate_topic_file(self, topic_name: str):
        """Generate topic entity file"""
        normalized_name = self.normalize_name(topic_name)
        file_path = self.base_path / "entities" / "topics" / f"{normalized_name}.md"
        
        # Find related meetings
        related_meetings = []
        for meeting in self.extracted_entities['meetings']:
            meeting_topics = [t.lower() for t in meeting.get('topics', [])]
            if topic_name.lower() in meeting_topics or any(topic_name.lower() in t for t in meeting_topics):
                related_meetings.append(meeting.get('title', 'Unknown Meeting'))
        
        # Find related technologies
        related_techs = []
        for tech in self.extracted_entities['technologies']:
            if topic_name.lower() in tech.lower() or tech.lower() in topic_name.lower():
                related_techs.append(tech)
        
        meetings_section = "\n".join([f"- [[{self.normalize_name(m)}|{m}]]" for m in related_meetings]) if related_meetings else "- (None identified)"
        techs_section = "\n".join([f"- [[{self.normalize_name(t)}|{t}]]" for t in related_techs[:10]]) if related_techs else "- (None identified)"
        
        content = f"""---
type: topic
name: {topic_name}
category: Strategic Initiative
status: Active
tags: [topic, strategic]
created: {datetime.now().strftime('%Y-%m-%d')}
---

# {topic_name}

## Overview
Strategic topic or initiative identified in HiveMind knowledge base.

## Related Meetings ({len(related_meetings)})
{meetings_section}

## Related Technologies
{techs_section}
"""
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        self.stats['topics_generated'] += 1
    
    def generate_meeting_file(self, meeting_data: Dict):
        """Generate meeting event file"""
        title = meeting_data.get('title', 'Unknown Meeting')
        normalized_title = self.normalize_name(title[:50])
        file_path = self.base_path / "events" / "meetings" / f"{normalized_title}.md"
        
        # Use resolved attendees if available
        attendees = meeting_data.get('attendees_resolved', meeting_data.get('attendees', []))
        attendees_text = "\n".join([f"- {att}" for att in attendees])
        topics_text = "\n".join([f"- {topic}" for topic in meeting_data.get('topics', [])])
        
        content = f"""---
type: meeting
title: {title}
date: {meeting_data.get('date', 'Unknown')}
attendees: {attendees}
tags: [meeting]
source: {meeting_data.get('source', '')}
created: {datetime.now().strftime('%Y-%m-%d')}
---

# {title}

**Date:** {meeting_data.get('date', 'Unknown')}

## Attendees
{attendees_text}

## Topics Discussed
{topics_text}
"""
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        self.stats['meetings_generated'] += 1
    
    def build(self):
        """Main build process using AI"""
        print("🚀 AI-Powered HiveMind Knowledge Builder")
        print("🤖 Using Azure OpenAI GPT-4 for intelligent extraction")
        print("📖 Following HiveMind Ontology v2.0")
        print("=" * 60)
        
        # Check if ontology exists
        ontology_path = self.base_path / "ontology.md"
        if ontology_path.exists():
            print("✓ Ontology loaded: markdown_files/ontology.md")
        else:
            print("⚠️  Warning: Ontology file not found")
        
        print("=" * 60)
        
        # Phase 1: LinkedIn profiles
        print("\n📋 Phase 1: AI Analysis of LinkedIn Profiles...")
        linkedin_dir = self.raw_input / "LinkedIn" / "Markdown (enhanced for AI interpretation)"
        if linkedin_dir.exists():
            md_files = list(linkedin_dir.glob("*.md"))
            print(f"  Found {len(md_files)} LinkedIn profiles")
            for file_path in md_files:
                self.process_linkedin_profile(file_path)
        
        # Phase 2: Meeting notes
        print("\n📋 Phase 2: AI Analysis of Meeting Notes...")
        meeting_dirs = [
            self.raw_input / "Internal Account Discussions",
            self.raw_input / "NNR meeting"
        ]
        total_meetings = 0
        for meeting_dir in meeting_dirs:
            if meeting_dir.exists():
                md_files = list(meeting_dir.glob("*.md"))
                total_meetings += len(md_files)
                for file_path in md_files:
                    self.process_meeting_notes(file_path)
        print(f"  Processed {total_meetings} meeting files")
        
        # Phase 3: PDFs
        print("\n📋 Phase 3: AI Analysis of PDF Documents...")
        pdf_files = list(self.raw_input.rglob("*.pdf"))
        # Filter to strategic docs only (avoid LinkedIn PDFs)
        strategic_pdfs = [p for p in pdf_files if 'AI Plan' in p.name or 'Annual Report' in p.name.lower()]
        print(f"  Found {len(strategic_pdfs)} strategic PDF documents")
        
        for file_path in strategic_pdfs:
            self.process_pdf_document(file_path)
        
        # Phase 4: DOCX files (meeting transcripts, decision maker lists)
        print("\n📋 Phase 4: AI Analysis of DOCX Documents...")
        docx_files = list(self.raw_input.rglob("*.docx"))
        print(f"  Found {len(docx_files)} DOCX files")
        
        if markitdown_converter:
            for file_path in docx_files:
                print(f"    🤖 Analyzing with GPT-4: {file_path.name}")
                self.process_docx_document(file_path)
        else:
            print("  ⚠️ markitdown not installed - install with: pip install markitdown")
        
        # Deduplicate entities
        print("\n📊 Deduplicating and consolidating entities...")
        org_before = len(self.extracted_entities['organizations'])
        tech_before = len(self.extracted_entities['technologies'])
        topics_before = len(self.extracted_entities['topics'])
        
        self.extracted_entities['organizations'] = list(set(self.extracted_entities['organizations']))
        self.extracted_entities['technologies'] = list(set(self.extracted_entities['technologies']))
        self.extracted_entities['topics'] = list(set(self.extracted_entities['topics']))
        
        print(f"  Organizations: {org_before} → {len(self.extracted_entities['organizations'])} (-{org_before - len(self.extracted_entities['organizations'])} duplicates)")
        print(f"  Technologies: {tech_before} → {len(self.extracted_entities['technologies'])} (-{tech_before - len(self.extracted_entities['technologies'])} duplicates)")
        print(f"  Topics: {topics_before} → {len(self.extracted_entities['topics'])} (-{topics_before - len(self.extracted_entities['topics'])} duplicates)")
        
        # Apply MIN_MENTIONS threshold to technologies
        MIN_MENTIONS = 2
        tech_counts = {}
        for tech in self.extracted_entities['technologies']:
            tech_counts[tech] = tech_counts.get(tech, 0) + 1
        
        tech_before_filter = len(self.extracted_entities['technologies'])
        self.extracted_entities['technologies'] = [
            tech for tech in self.extracted_entities['technologies'] 
            if tech_counts.get(tech, 0) >= MIN_MENTIONS or tech.lower() in ['azure', 'microsoft copilot', 'dynamics 365', 'power bi', 'databricks']
        ]
        print(f"  Technology filter (MIN_MENTIONS={MIN_MENTIONS}): {tech_before_filter} → {len(self.extracted_entities['technologies'])} technologies")
        
        # Consolidate technologies with GPT-4
        consolidated_tech = self.consolidate_technologies()
        if consolidated_tech:
            self.extracted_entities['technologies'] = consolidated_tech
        
        # Resolve meeting attendees
        print("\n👥 Resolving meeting attendees...")
        self.resolve_attendees()
        resolved_count = sum(1 for m in self.extracted_entities['meetings'] if m.get('attendees_resolved'))
        print(f"  ✓ Resolved attendees in {resolved_count} meetings")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 AI Extraction Summary:")
        print(f"  People: {len(self.extracted_entities['people'])}")
        print(f"  Organizations: {len(self.extracted_entities['organizations'])}")
        print(f"  Technologies: {len(self.extracted_entities['technologies'])}")
        print(f"  Topics: {len(self.extracted_entities['topics'])}")
        print(f"  Meetings: {len(self.extracted_entities['meetings'])}")
        print(f"  Relationships: {len(self.extracted_entities['relationships'])}")
        print(f"  AI Calls: {self.stats['ai_extractions']} (Errors: {self.stats['ai_errors']})")
        
        # Phase 5: Generate files
        print("\n📝 Phase 5: Generating Knowledge Base Files...")
        print("=" * 60)
        
        print(f"\n  👥 Creating {len(self.extracted_entities['people'])} people files...")
        for person in self.extracted_entities['people']:
            self.generate_person_file(person)
            print(f"    ✓ {person.get('name', 'Unknown')}")
        
        print(f"\n  🏢 Creating {len(self.extracted_entities['organizations'])} organization files...")
        for org in self.extracted_entities['organizations']:
            if org and org.lower() not in ['microsoft', 'unknown']:
                self.generate_organization_file(org)
                print(f"    ✓ {org}")
        
        print(f"\n  💻 Creating {len(self.extracted_entities['technologies'])} technology files...")
        tech_count = 0
        for tech in self.extracted_entities['technologies']:
            if tech:
                self.generate_technology_file(tech)
                tech_count += 1
                if tech_count <= 10:  # Show first 10
                    print(f"    ✓ {tech}")
        if tech_count > 10:
            print(f"    ... and {tech_count - 10} more")
        
        print(f"\n  📅 Creating {len(self.extracted_entities['meetings'])} meeting files...")
        for meeting in self.extracted_entities['meetings']:
            self.generate_meeting_file(meeting)
            print(f"    ✓ {meeting.get('title', 'Meeting')}")
        
        print(f"\n  📌 Creating {len(self.extracted_entities['topics'])} topic files...")
        for topic in self.extracted_entities['topics']:
            if topic:
                self.generate_topic_file(topic)
                print(f"    ✓ {topic}")
        
        # Calculate statistics
        from collections import Counter
        all_techs_raw = []
        for meeting in self.extracted_entities['meetings']:
            all_techs_raw.extend(meeting.get('topics', []))
        tech_counter = Counter(self.extracted_entities['technologies'])
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ AI-Powered Knowledge Graph Complete!")
        print(f"  People: {self.stats['people_generated']}")
        print(f"  Organizations: {self.stats['orgs_generated']}")
        print(f"  Technologies: {self.stats['tech_generated']}")
        print(f"  Topics: {self.stats['topics_generated']}")
        print(f"  Meetings: {self.stats['meetings_generated']}")
        
        # Show top technologies
        if tech_counter:
            top_techs = tech_counter.most_common(5)
            print(f"\n📊 Most Mentioned Technologies:")
            for tech, count in top_techs:
                print(f"  • {tech}: {count} mentions")
        
        # Show relationship statistics
        if self.extracted_entities['relationships']:
            from collections import Counter
            rel_types = Counter([r.get('type') for r in self.extracted_entities['relationships']])
            print(f"\n🔗 Relationship Summary:")
            for rel_type, count in rel_types.most_common():
                print(f"  • {rel_type}: {count} relationships")
        
        print(f"\n🤖 Powered by Azure OpenAI GPT-4 ({self.stats['ai_extractions']} API calls)")


if __name__ == "__main__":
    builder = AIKnowledgeBuilder()
    builder.build()
