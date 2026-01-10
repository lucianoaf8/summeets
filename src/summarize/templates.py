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
    REQUIREMENTS = "requirements"


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
    
    REQUIREMENTS = TemplateConfig(
        name="Requirements Extraction v3",
        description="Produce an audit-ready, exhaustive requirements report from meeting transcripts.",
        system_prompt=(
            "You are a senior requirements analyst. Your task is NOT to produce a generic meeting summary. "
            "Generate a complete, structured requirements report suitable for handoff to data, engineering, and PM. "
            "Capture objectives, scope, stakeholders, explicit and implicit requirements, KPIs with formulas, data sources, "
            "integration points, assumptions, constraints, dependencies, risks, and next steps. "
            "Identify gaps and open questions without guessing. Where information is missing, mark it clearly as TBC/TBD.\n\n"
            "Thinking policy: perform deep internal reasoning before writing; do NOT include your internal notes in the output. "
            "Return only the final structured report with all sections present in the exact order specified."
        ),
        user_prompt_template=(
            "<scratchpad>\n"
            "Plan (do NOT output this block):\n"
            "1) Determine business context and core objective(s). 2) Extract explicit requirements. "
            "3) Infer implicit requirements and dependencies. 4) Categorize (Functional, Non-Functional, Data, Reporting, Integration). "
            "5) Define KPIs with formula templates, inputs, grain, window, and edge cases. "
            "6) Inventory data sources, ownership, access and refresh. 7) Identify systems and integration points. "
            "8) List assumptions, constraints, risks, and open questions. 9) Specify deliverables, formats, and timelines. "
            "10) Map traceability from requirements to KPIs, data, and deliverables. Validate completeness.\n"
            "</scratchpad>\n\n"
            "Analyze the transcript below and output a comprehensive requirements report.\n\n"
            "{transcript}\n\n"
            "Output rules:\n"
            "- Use ONLY the section order below. Include every section, even if empty (write 'None found').\n"
            "- Use numbered IDs: R-#, KPI-#, DS-#, INT-#, A-# (assumptions), C-# (constraints), D-# (dependencies), "
            "RK-# (risks), Q-# (open questions), AI-# (action items).\n"
            "- For KPIs, include: Purpose, Formula, Inputs (with source refs), Grain & Window, Filters, Edge Cases, "
            "Data Quality Checks, Owner, Refresh Cadence, Acceptance Criteria.\n"
            "- For Data Sources, include: System, Tables/Objects (if known), Grain, Join Keys, Freshness, Latency/SLA, "
            "Access/Permissions, Known Quality Issues.\n"
            "- For Integrations, include: Systems, Direction, Triggers, Contracts/Schemas, Error Handling, Retries, SLAs.\n"
            "- Do not invent facts. Mark missing facts as TBC/TBD and add a matching Q-#.\n"
            "- Keep language precise and implementation-ready."
        ),
        max_tokens=8000,  # Must be > thinking_budget (6000)
        sections=[
            # 1
            "Core Objective & Business Context",
            # 2
            "In-Scope vs Out-of-Scope",
            # 3
            "Stakeholders & Roles",
            # 4
            "Functional Requirements",
            # 5
            "Non-Functional Requirements",
            # 6
            "Data Requirements",
            # 7
            "KPIs & Metrics",
            # 8
            "Reports & Deliverables",
            # 9
            "Systems & Integrations",
            # 10
            "Data Sources & Technical Specs",
            # 11
            "Assumptions",
            # 12
            "Constraints",
            # 13
            "Dependencies",
            # 14
            "Risks",
            # 15
            "Open Questions",
            # 16
            "Action Items & Timeline",
            # 17
            "Traceability Matrix (R ↔ KPI ↔ Data Source ↔ Deliverable)",
            # 18
            "Quality Gate Checklist"
        ]
    )

    
    @classmethod
    def get_template(cls, template_type: SummaryTemplate) -> TemplateConfig:
        """Get template configuration by type."""
        templates = {
            SummaryTemplate.DEFAULT: cls.DEFAULT,
            SummaryTemplate.SOP: cls.SOP,
            SummaryTemplate.DECISION: cls.DECISION,
            SummaryTemplate.BRAINSTORM: cls.BRAINSTORM,
            SummaryTemplate.REQUIREMENTS: cls.REQUIREMENTS
        }
        return templates[template_type]
    
    @classmethod
    def list_templates(cls) -> Dict[str, str]:
        """List available templates with descriptions."""
        return {
            SummaryTemplate.DEFAULT: cls.DEFAULT.description,
            SummaryTemplate.SOP: cls.SOP.description,
            SummaryTemplate.DECISION: cls.DECISION.description,
            SummaryTemplate.BRAINSTORM: cls.BRAINSTORM.description,
            SummaryTemplate.REQUIREMENTS: cls.REQUIREMENTS.description
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
    
    # Requirements indicators
    requirements_keywords = [
        "requirement", "requirements", "specification", "specs", "criteria", 
        "must have", "should have", "need to", "necessary", "mandatory",
        "deliverable", "output", "report", "dashboard", "analysis",
        "data source", "field", "column", "format", "layout", "template",
        "calculation", "formula", "filter", "grouping", "breakdown",
        "business rule", "logic", "workflow", "process", "integration",
        "api", "database", "table", "query", "export", "import",
        "user access", "permission", "role", "authentication",
        "performance", "speed", "latency", "scalability", "volume",
        "compliance", "regulation", "audit", "security", "validation",
        "deliverable", "timeline", "deadline", "milestone", "phase"
    ]
    
    # Count keyword occurrences
    sop_score = sum(1 for keyword in sop_keywords if keyword in text_lower)
    decision_score = sum(1 for keyword in decision_keywords if keyword in text_lower)
    brainstorm_score = sum(1 for keyword in brainstorm_keywords if keyword in text_lower)
    requirements_score = sum(1 for keyword in requirements_keywords if keyword in text_lower)
    
    # Return highest scoring type
    scores = {
        SummaryTemplate.SOP: sop_score,
        SummaryTemplate.DECISION: decision_score, 
        SummaryTemplate.BRAINSTORM: brainstorm_score,
        SummaryTemplate.REQUIREMENTS: requirements_score
    }
    
    max_score = max(scores.values())
    if max_score >= 3:  # Minimum threshold
        return max(scores, key=scores.get)
    
    return SummaryTemplate.DEFAULT