#!/usr/bin/env python3
"""Simple test to verify template system functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.summarize.templates import SummaryTemplates, detect_meeting_type
    from core.models import SummaryTemplate
except ImportError as e:
    print(f"Import error: {e}")
    print("This test requires the dependencies to be installed.")
    print("Run: pip install -e .")
    sys.exit(1)

def test_template_system():
    """Test template system basic functionality."""
    print("=== Testing Template System ===\n")
    
    # Test template listing
    print("1. Available templates:")
    templates = SummaryTemplates.list_templates()
    for name, desc in templates.items():
        print(f"   {name}: {desc}")
    print()
    
    # Test template configuration
    print("2. SOP Template Configuration:")
    sop_config = SummaryTemplates.get_template(SummaryTemplate.SOP)
    print(f"   Name: {sop_config.name}")
    print(f"   Max Tokens: {sop_config.max_tokens}")
    print(f"   Sections: {sop_config.sections}")
    print()
    
    # Test auto-detection
    print("3. Auto-detection tests:")
    
    test_texts = {
        "SOP meeting": """
        [Instructor]: Now I'll show you how to configure the system step by step.
        First, you need to open the configuration file located at /etc/config/app.conf.
        Then set the database connection string. Let me walk you through the process.
        """,
        
        "Decision meeting": """
        [Manager]: We need to decide between option A and option B for the new feature.
        [Developer]: I recommend option A because it has better performance.
        [Manager]: Let's vote on this decision. All in favor of option A?
        """,
        
        "Brainstorm meeting": """
        [Leader]: Let's generate some creative ideas for the marketing campaign.
        [Member1]: What if we use social media influencers?
        [Member2]: Maybe we could create an interactive website experience.
        [Leader]: Great ideas! Any other suggestions?
        """,
        
        "General meeting": """
        [Manager]: Let's review the quarterly results and discuss next steps.
        [Analyst]: Sales increased by 15% compared to last quarter.
        [Manager]: That's good progress. What are the action items for next quarter?
        """
    }
    
    for meeting_type, text in test_texts.items():
        detected = detect_meeting_type(text)
        print(f"   {meeting_type} -> {detected.value}")
    
    print("\n✓ Template system test completed successfully!")

if __name__ == "__main__":
    test_template_system()
    
    # Cleanup note
    print("\nTo test with a real transcript:")
    print("1. Install dependencies: pip install -e .")
    print("2. Create a .env file with your API keys")
    print("3. Run: summeets templates  # to see available templates")
    print("4. Run: summeets summarize transcript.json --template sop")