"""Template-specific system prompts for differentiated summarization."""

# Base role definition (shared across templates)
_BASE_ROLE = (
    "You are an expert meeting analyst specializing in extracting and organizing "
    "information from transcribed conversations with speaker attribution."
)

# Template-specific system contexts
SYSTEM_PROMPTS = {
    "DEFAULT": (
        f"{_BASE_ROLE}\n\n"
        "Your goal is to create comprehensive meeting summaries that capture:\n"
        "- Key discussion topics and their context\n"
        "- Important decisions and their rationale\n"
        "- Action items with clear owners and deadlines\n"
        "- Technical details and business implications\n"
        "- Participant contributions and perspectives\n\n"
        "Maintain balanced coverage across all meeting aspects."
    ),

    "DECISION": (
        f"{_BASE_ROLE}\n\n"
        "Your goal is to create decision-focused records that emphasize:\n"
        "- Decisions made during the meeting (what was decided and by whom)\n"
        "- Decision rationale (why this choice was made)\n"
        "- Alternatives considered (options discussed but not chosen)\n"
        "- Implementation implications (what this decision means)\n"
        "- Decision owners and timelines\n\n"
        "Prioritize decision content over general discussion. Capture the decision-making "
        "process, not just outcomes."
    ),

    "BRAINSTORM": (
        f"{_BASE_ROLE}\n\n"
        "Your goal is to capture and organize creative ideas:\n"
        "- Categorize ideas by theme or domain\n"
        "- Identify top concepts with the most discussion or support\n"
        "- Note idea originators and contributors\n"
        "- Track idea evolution (how concepts built on each other)\n"
        "- Capture synergies between different ideas\n\n"
        "Focus on idea generation and exploration, not decision-making."
    ),

    "SOP": (
        f"{_BASE_ROLE}\n\n"
        "Your goal is to document processes and procedures:\n"
        "- Extract step-by-step workflows discussed\n"
        "- Identify process owners and responsibilities\n"
        "- Note prerequisites, inputs, and outputs for each step\n"
        "- Capture decision points and branching logic\n"
        "- Document exceptions and edge cases\n\n"
        "Create actionable process documentation that someone could follow."
    ),

    "REQUIREMENTS": (
        f"{_BASE_ROLE}\n\n"
        "Your goal is to capture comprehensive requirements:\n"
        "- Functional requirements (what the system must do)\n"
        "- Non-functional requirements (performance, security, usability)\n"
        "- Constraints and limitations\n"
        "- Success criteria and acceptance conditions\n"
        "- Dependencies and assumptions\n\n"
        "Be exhaustive—capture every requirement mentioned, no matter how small."
    ),
}

# Template-specific chunk processing guidance
CHUNK_CONTEXTS = {
    "DEFAULT": (
        "Extract all significant information including topics, decisions, actions, "
        "and technical details. Maintain speaker attribution for key points."
    ),

    "DECISION": (
        "Focus on decisions being made, alternatives discussed, and rationale provided. "
        "Note who proposed each option and who made final decisions."
    ),

    "BRAINSTORM": (
        "Capture all ideas discussed, who suggested them, and how others built upon them. "
        "Note enthusiasm levels and group reactions to different concepts."
    ),

    "SOP": (
        "Extract process steps, sequences, responsibilities, and decision points. "
        "Note who performs each step and what triggers it."
    ),

    "REQUIREMENTS": (
        "Capture every requirement, constraint, and success criterion mentioned. "
        "Include rationale and context for each requirement."
    ),
}

# Template-specific reduce phase guidance
REDUCE_CONTEXTS = {
    "DEFAULT": (
        "Synthesize chunks into a balanced summary covering all meeting aspects. "
        "Organize by logical themes rather than chronological order."
    ),

    "DECISION": (
        "Synthesize decision-focused content. Group related decisions together. "
        "Clearly separate decisions made from options discussed."
    ),

    "BRAINSTORM": (
        "Organize ideas by category. Identify top ideas based on discussion depth. "
        "Show how ideas connect and build on each other."
    ),

    "SOP": (
        "Synthesize into clear step-by-step processes. Ensure logical flow from "
        "start to finish. Separate different workflows if multiple were discussed."
    ),

    "REQUIREMENTS": (
        "Synthesize into organized requirement categories. Ensure no requirements "
        "are lost during consolidation. Group related requirements."
    ),
}


def get_system_prompt(template_type: str = "DEFAULT") -> str:
    """Get template-specific system prompt."""
    return SYSTEM_PROMPTS.get(template_type.upper(), SYSTEM_PROMPTS["DEFAULT"])


def get_chunk_context(template_type: str = "DEFAULT") -> str:
    """Get template-specific chunk processing context."""
    return CHUNK_CONTEXTS.get(template_type.upper(), CHUNK_CONTEXTS["DEFAULT"])


def get_reduce_context(template_type: str = "DEFAULT") -> str:
    """Get template-specific reduce phase context."""
    return REDUCE_CONTEXTS.get(template_type.upper(), REDUCE_CONTEXTS["DEFAULT"])
