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
            'meetings': []
        }
        
        self.stats = defaultdict(int)
    
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
Extract structured entities from documents. Return JSON only, no markdown formatting.

For LinkedIn profiles, extract:
- Full name, current role, company, location, key skills (5-7 most important)

For meeting notes, extract:
- Meeting title, date (parse from text), key attendees (full names only), main topics discussed (3-5), technologies mentioned

For technical documents, extract:
- Organization names, technologies/platforms mentioned, strategic topics

Return in this exact JSON format:
{
  "people": [{"name": "Full Name", "role": "Job Title", "company": "Company", "location": "City, Country", "skills": ["skill1", "skill2"]}],
  "organizations": ["Company Name"],
  "technologies": ["Technology Name"],
  "topics": ["Topic description"],
  "meetings": [{"title": "Meeting Title", "date": "YYYY-MM-DD or Q4 2025", "attendees": ["Name1", "Name2"], "topics": ["topic1"]}]
}

Only include entities that are clearly mentioned. Use empty arrays if not applicable."""

        user_prompt = f"""Document Type: {document_type}
Source: {source_file}

Document Content:
{text[:8000]}

Extract all relevant entities."""

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
            return entities
            
        except Exception as e:
            print(f"  ⚠️ AI extraction error: {e}")
            self.stats['ai_errors'] += 1
            return {'people': [], 'organizations': [], 'technologies': [], 'topics': [], 'meetings': []}
    
    def process_linkedin_profile(self, file_path: Path):
        """Process LinkedIn profile with AI"""
        content = file_path.read_text(encoding='utf-8')
        
        print(f"    🤖 Analyzing with GPT-4: {file_path.name}")
        entities = self.extract_entities_with_ai(content, str(file_path), "LinkedIn Profile")
        
        # Store extracted people
        for person in entities.get('people', []):
            person['source'] = str(file_path)
            person['type'] = 'linkedin-profile'
            self.extracted_entities['people'].append(person)
        
        # Store other entities
        self.extracted_entities['organizations'].extend(entities.get('organizations', []))
        self.extracted_entities['technologies'].extend(entities.get('technologies', []))
    
    def process_meeting_notes(self, file_path: Path):
        """Process meeting notes with AI"""
        content = file_path.read_text(encoding='utf-8')
        
        print(f"    🤖 Analyzing with GPT-4: {file_path.name}")
        entities = self.extract_entities_with_ai(content, str(file_path), "Meeting Notes")
        
        # Store meetings
        for meeting in entities.get('meetings', []):
            meeting['source'] = str(file_path)
            self.extracted_entities['meetings'].append(meeting)
        
        # Store topics and technologies
        self.extracted_entities['topics'].extend(entities.get('topics', []))
        self.extracted_entities['technologies'].extend(entities.get('technologies', []))
    
    def process_pdf_document(self, file_path: Path):
        """Process PDF with AI"""
        text = self.extract_text_from_pdf(file_path)
        if not text:
            return
        
        print(f"    🤖 Analyzing with GPT-4: {file_path.name}")
        
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
        text = self.extract_text_from_docx(file_path)
        if not text or len(text) < 50:  # Skip if extraction failed or too short
            return
        
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
    
    def generate_person_file(self, person_data: Dict):
        """Generate person entity file"""
        name = person_data['name']
        normalized_name = self.normalize_name(name)
        file_path = self.base_path / "entities" / "people" / f"{normalized_name}.md"
        
        skills_text = "\n".join([f"- {skill}" for skill in person_data.get('skills', [])])
        
        content = f"""---
type: person
name: {name}
role: {person_data.get('role', 'Unknown')}
organization: {person_data.get('company', 'Unknown')}
location: {person_data.get('location', 'Unknown')}
tags: [linkedin-profile, {self.normalize_name(person_data.get('company', ''))}]
source: {person_data.get('source', '')}
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
        
        people_section = "\n".join(people_links) if people_links else "- (None listed)"
        
        content = f"""---
type: organization
name: {org_name}
tags: [organization]
created: {datetime.now().strftime('%Y-%m-%d')}
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
    
    def generate_meeting_file(self, meeting_data: Dict):
        """Generate meeting event file"""
        title = meeting_data.get('title', 'Unknown Meeting')
        normalized_title = self.normalize_name(title[:50])
        file_path = self.base_path / "events" / "meetings" / f"{normalized_title}.md"
        
        attendees_text = "\n".join([f"- {att}" for att in meeting_data.get('attendees', [])])
        topics_text = "\n".join([f"- {topic}" for topic in meeting_data.get('topics', [])])
        
        content = f"""---
type: meeting
title: {title}
date: {meeting_data.get('date', 'Unknown')}
attendees: {meeting_data.get('attendees', [])}
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
        print("\n📊 Deduplicating entities...")
        self.extracted_entities['organizations'] = list(set(self.extracted_entities['organizations']))
        self.extracted_entities['technologies'] = list(set(self.extracted_entities['technologies']))
        self.extracted_entities['topics'] = list(set(self.extracted_entities['topics']))
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 AI Extraction Summary:")
        print(f"  People: {len(self.extracted_entities['people'])}")
        print(f"  Organizations: {len(self.extracted_entities['organizations'])}")
        print(f"  Technologies: {len(self.extracted_entities['technologies'])}")
        print(f"  Topics: {len(self.extracted_entities['topics'])}")
        print(f"  Meetings: {len(self.extracted_entities['meetings'])}")
        print(f"  AI Calls: {self.stats['ai_extractions']} (Errors: {self.stats['ai_errors']})")
        
        # Phase 4: Generate files
        print("\n📝 Generating Knowledge Base Files...")
        
        print(f"  Creating {len(self.extracted_entities['people'])} people files...")
        for person in self.extracted_entities['people']:
            self.generate_person_file(person)
        
        print(f"  Creating {len(self.extracted_entities['organizations'])} organization files...")
        for org in self.extracted_entities['organizations']:
            if org and org.lower() not in ['microsoft', 'unknown']:
                self.generate_organization_file(org)
        
        print(f"  Creating {len(self.extracted_entities['technologies'])} technology files...")
        for tech in self.extracted_entities['technologies']:
            if tech:
                self.generate_technology_file(tech)
        
        print(f"  Creating {len(self.extracted_entities['meetings'])} meeting files...")
        for meeting in self.extracted_entities['meetings']:
            self.generate_meeting_file(meeting)
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ AI-Powered Knowledge Graph Complete!")
        print(f"  People: {self.stats['people_generated']}")
        print(f"  Organizations: {self.stats['orgs_generated']}")
        print(f"  Technologies: {self.stats['tech_generated']}")
        print(f"  Meetings: {self.stats['meetings_generated']}")
        print(f"\n🤖 Powered by Azure OpenAI GPT-4")


if __name__ == "__main__":
    builder = AIKnowledgeBuilder()
    builder.build()
