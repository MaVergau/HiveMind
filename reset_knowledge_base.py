"""
Reset Script for HiveMind Knowledge Base

Deletes all generated markdown files while preserving templates
and folder structure for a clean rebuild.
"""

from pathlib import Path
import shutil


def reset_knowledge_base(markdown_dir: Path):
    """Delete all generated files, keep templates and structure"""
    
    print("🗑️  Resetting HiveMind Knowledge Base...")
    print("=" * 50)
    
    deleted_count = 0
    
    # Reset entity directories
    for entity_type in ['people', 'organizations', 'technologies', 'topics']:
        entity_dir = markdown_dir / 'entities' / entity_type
        if entity_dir.exists():
            files = [f for f in entity_dir.glob('*.md') 
                    if f.name not in ['TEMPLATE.md', 'INDEX.md']]
            
            print(f"\n📁 Cleaning {entity_type}... ({len(files)} files)")
            for file_path in files:
                file_path.unlink()
                deleted_count += 1
            
            if files:
                print(f"  ✓ Deleted {len(files)} files")
    
    # Reset event directories
    for event_type in ['meetings', 'decisions', 'milestones']:
        event_dir = markdown_dir / 'events' / event_type
        if event_dir.exists():
            files = [f for f in event_dir.glob('*.md') 
                    if f.name not in ['TEMPLATE.md']]
            
            if files:
                print(f"\n📅 Cleaning {event_type}... ({len(files)} files)")
                for file_path in files:
                    file_path.unlink()
                    deleted_count += 1
                print(f"  ✓ Deleted {len(files)} files")
    
    # Delete any index files that were generated
    for index_file in markdown_dir.rglob('INDEX.md'):
        if index_file.exists():
            index_file.unlink()
            deleted_count += 1
    
    print(f"\n\n✅ Reset complete!")
    print(f"   Deleted {deleted_count} generated files")
    print(f"   Templates and folder structure preserved")
    print(f"\n🚀 Ready to run: python build_proximus_knowledge.py")


def main():
    """Main execution"""
    base_dir = Path(__file__).parent
    markdown_dir = base_dir / 'markdown_files'
    
    if not markdown_dir.exists():
        print(f"❌ Markdown directory not found: {markdown_dir}")
        return
    
    # Confirm before deleting
    print("⚠️  This will delete all generated markdown files.")
    print("   Templates and folder structure will be preserved.")
    response = input("\nContinue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        reset_knowledge_base(markdown_dir)
    else:
        print("\n❌ Reset cancelled")


if __name__ == '__main__':
    main()
