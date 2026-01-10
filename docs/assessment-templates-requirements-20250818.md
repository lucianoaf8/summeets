# Templates Assessment - Requirements Template Issues
**Date**: 2025-08-18
**Assessor**: Claude AI
**Scope**: core/summarize/templates.py REQUIREMENTS template and output quality
**Version**: Current

## Executive Summary

The REQUIREMENTS template in `core/summarize/templates.py` is fundamentally broken and produces unusable output. Instead of extracting requirements from meeting transcripts, it generates generic meta-commentary about meeting summarization principles. The template's complex, overly prescriptive prompts confuse the LLM and result in outputs that completely ignore the actual transcript content.

Key findings:
- Template produces meta-commentary instead of requirements extraction
- Overly complex prompts with excessive formatting instructions
- Output doesn't match template's intended purpose
- Default template would produce better results for any meeting type

## Assessment Methodology

1. Analyzed template code structure and prompt design
2. Reviewed actual output files from requirements template usage
3. Compared template design against other working templates
4. Identified root causes of template failure

## Detailed Findings

### Critical Issues

#### 1. Fundamental Template Failure (Priority: CRITICAL)
**Location**: `core/summarize/templates.py:138-193`
**Issue**: The REQUIREMENTS template produces completely unrelated output
**Evidence**: Output file contains generic advice about meeting summarization instead of extracted requirements
**Impact**: Template is completely unusable for its intended purpose

#### 2. Overly Complex and Confusing Prompts (Priority: CRITICAL)
**Location**: Lines 149-171 (user_prompt_template)
**Issue**: 23-line prompt with excessive formatting requirements confuses the LLM
**Problems**:
- Too many competing instructions
- Overemphasis on structure over content extraction
- Contradictory directives (extract requirements vs. ignore discussion)
- Excessive use of ALL CAPS and formatting demands

#### 3. Inappropriate Negative Instructions (Priority: HIGH)
**Location**: Lines 150-151, 168-170
**Issue**: Multiple "DO NOT" statements create confusion
**Examples**:
- "DO NOT create a meeting summary"
- "Ignore general discussion unless it contains specific requirements"
**Impact**: LLM focuses on what NOT to do rather than the actual task

#### 4. Template Auto-Detection Issues (Priority: MEDIUM)
**Location**: Lines 270-297 (detect_meeting_type function)
**Issue**: Requirements keywords are too broad and will trigger incorrectly
**Impact**: May auto-select broken template for general meetings

### Positive Findings

#### Working Templates
- DEFAULT template: Clean, effective prompts producing good results
- SOP template: Comprehensive but focused prompts
- DECISION template: Clear structure and appropriate complexity
- BRAINSTORM template: Well-balanced instructions

## Recommendations

### Immediate Actions (Priority 1)

#### 1. Complete Requirements Template Rewrite
**Action**: Replace current REQUIREMENTS template with simplified, effective version
**Justification**: Current template is beyond repair - simpler approach needed

```python
REQUIREMENTS = TemplateConfig(
    name="Requirements Extraction",
    description="Extract requirements, specifications, and deliverables from meetings",
    system_prompt=(
        "You are a business analyst extracting requirements from meeting discussions. "
        "Identify what needs to be built, implemented, or delivered. Focus on "
        "specific, actionable requirements mentioned in the conversation."
    ),
    user_prompt_template=(
        "Extract all requirements from this meeting transcript:\n\n{transcript}\n\n"
        "Organize findings into:\n"
        "- Functional Requirements (features, capabilities)\n"
        "- Technical Requirements (systems, integrations, tools)\n" 
        "- Business Requirements (objectives, constraints)\n"
        "- Data Requirements (information, reports, sources)\n"
        "- Timeline & Dependencies"
    ),
    max_tokens=3000,
    sections=[
        "Functional Requirements",
        "Technical Requirements", 
        "Business Requirements",
        "Data Requirements",
        "Timeline & Dependencies"
    ]
)
```

#### 2. Remove Overly Complex Instructions
**Action**: Eliminate all-caps text, excessive formatting demands, and negative instructions
**Target**: Reduce prompt complexity by 70%

#### 3. Test Template with Sample Transcripts
**Action**: Validate new template produces actual requirements extraction
**Method**: Test with known meeting transcripts containing clear requirements

### Short-term Actions (Priority 2)

#### 1. Review Other Templates for Similar Issues
**Action**: Audit remaining templates for prompt complexity issues
**Focus**: Ensure prompts are clear, focused, and actionable

#### 2. Improve Auto-Detection Logic
**Action**: Refine keyword matching for requirements detection
**Method**: Use more specific requirements-related terms

#### 3. Add Template Validation
**Action**: Implement output quality checks for each template type
**Purpose**: Detect when templates produce off-topic results

### Long-term Actions (Priority 3)

#### 1. Template Testing Framework
**Action**: Create automated tests for each template with sample inputs
**Benefit**: Prevent regression when modifying templates

#### 2. Template Performance Metrics
**Action**: Track which templates produce highest quality outputs
**Method**: User feedback and automated quality scoring

#### 3. Dynamic Template Selection
**Action**: Improve auto-detection using semantic analysis
**Enhancement**: Use embedding similarity instead of keyword matching

## Risk Assessment

### Current Risks
- **Critical**: REQUIREMENTS template is completely broken, producing unusable output
- **High**: Users may lose trust in template system due to poor results
- **Medium**: Auto-detection may select broken template inappropriately

### Mitigation Strategies
- Immediate template replacement eliminates critical risk
- Clear documentation of template purposes and expected outputs
- Fallback to DEFAULT template when specialized templates fail

## Conclusion

The REQUIREMENTS template requires immediate replacement. The current implementation is fundamentally flawed with overly complex prompts that confuse rather than guide the LLM. A simplified approach focusing on clear, direct instructions will dramatically improve results.

The other templates in the system demonstrate good practices - the DEFAULT template's simplicity and clarity should be the model for the requirements rewrite.

## Appendix

### Evidence of Template Failure
**Expected Output**: Extracted requirements, specifications, deliverables from meeting
**Actual Output**: Meta-commentary about meeting summarization best practices
**Root Cause**: Overly complex prompts with competing instructions

### Template Complexity Comparison
- **DEFAULT**: 2 simple, clear instructions = Effective results
- **REQUIREMENTS**: 23 lines with formatting demands = Complete failure
- **Recommendation**: Match DEFAULT template's simplicity and clarity