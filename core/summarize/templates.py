"""Summary templates for different meeting types."""
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass


class SummaryTemplate(str, Enum):
    """Available summary templates."""
    DEFAULT = "default"
    SOP = "sop"
    DECISION = "decision"
    BRAINSTORM = "brainstorm"


@dataclass
class TemplateConfig:
    """Configuration for a summary template."""
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    max_tokens: int
    sections: List[str]
    special_instructions: str = ""


class SummaryTemplates:
    """Collection of summary templates for different meeting types."""
    
    DEFAULT = TemplateConfig(
        name="Default Meeting Summary",
        description="Comprehensive summary for general meetings",
        system_prompt=(
            "You are an expert meeting summarizer. Create a comprehensive summary "
            "that captures key points, decisions, action items, and important discussions. "
            "Focus on actionable insights and clear outcomes."
        ),
        user_prompt_template=(
            "Summarize this meeting transcript:\n\n{transcript}\n\n"
            "Create a comprehensive summary with key points, decisions, and action items."
        ),
        max_tokens=3000,
        sections=[
            "Meeting Overview",
            "Key Discussion Points", 
            "Decisions Made",
            "Action Items",
            "Next Steps"
        ]
    )
    
    SOP = TemplateConfig(
        name="Standard Operating Procedure",
        description="Process documentation for training/instructional meetings",
        system_prompt=(
            "You are an expert technical writer creating Standard Operating Procedures (SOPs). "
            "Extract step-by-step processes, file references, system information, and create "
            "a comprehensive guide that enables someone to replicate the exact process shown. "
            "Focus on technical accuracy, completeness, and usability."
        ),
        user_prompt_template=(
            "Create a Standard Operating Procedure (SOP) from this training/process meeting:\n\n{transcript}\n\n"
            "Extract:\n"
            "1. Complete step-by-step process guide\n"
            "2. All files mentioned (names, locations, purposes)\n" 
            "3. System requirements and prerequisites\n"
            "4. Common issues and troubleshooting\n"
            "5. Reference materials and resources\n\n"
            "The SOP should be detailed enough for someone to follow without the original meeting."
        ),
        max_tokens=5000,
        sections=[
            "Process Overview",
            "Prerequisites & Requirements",
            "Step-by-Step Instructions",
            "File References",
            "System Configuration",
            "Troubleshooting",
            "Additional Resources",
            "Meeting Summary"
        ],
        special_instructions=(
            "Pay special attention to:\n"
            "- File paths and locations\n"
            "- Specific commands or code snippets\n"
            "- Configuration settings\n"
            "- Dependencies and requirements\n"
            "- Error handling and common issues"
        )
    )
    
    DECISION = TemplateConfig(
        name="Decision Record",
        description="Focus on decisions and their rationale",
        system_prompt=(
            "You are an expert at documenting decision-making processes. "
            "Extract and clearly document all decisions made, their rationale, "
            "alternatives considered, and implementation plans."
        ),
        user_prompt_template=(
            "Create a decision record from this meeting:\n\n{transcript}\n\n"
            "Focus on decisions made, rationale, alternatives considered, and next steps."
        ),
        max_tokens=2500,
        sections=[
            "Decisions Summary",
            "Context & Background",
            "Options Considered", 
            "Decision Rationale",
            "Implementation Plan",
            "Risks & Mitigation"
        ]
    )
    
    BRAINSTORM = TemplateConfig(
        name="Brainstorming Session",
        description="Capture ideas and creative discussions",
        system_prompt=(
            "You are an expert at organizing and categorizing creative ideas. "
            "Capture all ideas discussed, group them by theme, and identify "
            "the most promising concepts for further development."
        ),
        user_prompt_template=(
            "Organize this brainstorming meeting:\n\n{transcript}\n\n"
            "Categorize ideas, note creative concepts, and identify next steps for promising ideas."
        ),
        max_tokens=3500,
        sections=[
            "Session Overview",
            "Ideas by Category",
            "Top Concepts",
            "Implementation Ideas",
            "Follow-up Actions"
        ]
    )
    
    @classmethod
    def get_template(cls, template_type: SummaryTemplate) -> TemplateConfig:
        """Get template configuration by type."""
        templates = {
            SummaryTemplate.DEFAULT: cls.DEFAULT,
            SummaryTemplate.SOP: cls.SOP,
            SummaryTemplate.DECISION: cls.DECISION,
            SummaryTemplate.BRAINSTORM: cls.BRAINSTORM
        }
        return templates[template_type]
    
    @classmethod
    def list_templates(cls) -> Dict[str, str]:
        """List available templates with descriptions."""
        return {
            SummaryTemplate.DEFAULT: cls.DEFAULT.description,
            SummaryTemplate.SOP: cls.SOP.description,
            SummaryTemplate.DECISION: cls.DECISION.description,
            SummaryTemplate.BRAINSTORM: cls.BRAINSTORM.description
        }


def format_sop_output(summary: str, template_config: TemplateConfig) -> str:
    """Format SOP summary with enhanced structure."""
    if template_config.name != "Standard Operating Procedure":
        return summary
    
    # Add SOP-specific formatting
    header = f"""# Standard Operating Procedure
**Generated from Meeting Recording**
**Date:** {{timestamp}}
**Type:** Process Documentation

---

"""
    
    # Ensure proper SOP structure
    if "## File References" not in summary:
        summary += "\n\n## File References\n*No specific files were mentioned in this recording.*"
    
    if "## System Configuration" not in summary:
        summary += "\n\n## System Configuration\n*No specific system configuration details were mentioned.*"
    
    if "## Troubleshooting" not in summary:
        summary += "\n\n## Troubleshooting\n*No troubleshooting information was provided in this recording.*"
    
    return header + summary


def detect_meeting_type(transcript_text: str) -> SummaryTemplate:
    """Auto-detect meeting type based on content keywords."""
    text_lower = transcript_text.lower()
    
    # SOP/Process indicators
    sop_keywords = [
        "step by step", "how to", "process", "procedure", "tutorial", 
        "training", "guide", "instruction", "configure", "setup",
        "install", "deploy", "walkthrough", "demonstration"
    ]
    
    # Decision meeting indicators  
    decision_keywords = [
        "decision", "decide", "choose", "option", "alternative",
        "recommendation", "approve", "reject", "vote", "consensus"
    ]
    
    # Brainstorming indicators
    brainstorm_keywords = [
        "idea", "brainstorm", "creative", "innovative", "concept",
        "suggestion", "possibility", "what if", "maybe we could"
    ]
    
    # Count keyword occurrences
    sop_score = sum(1 for keyword in sop_keywords if keyword in text_lower)
    decision_score = sum(1 for keyword in decision_keywords if keyword in text_lower)
    brainstorm_score = sum(1 for keyword in brainstorm_keywords if keyword in text_lower)
    
    # Return highest scoring type
    scores = {
        SummaryTemplate.SOP: sop_score,
        SummaryTemplate.DECISION: decision_score, 
        SummaryTemplate.BRAINSTORM: brainstorm_score
    }
    
    max_score = max(scores.values())
    if max_score >= 3:  # Minimum threshold
        return max(scores, key=scores.get)
    
    return SummaryTemplate.DEFAULT