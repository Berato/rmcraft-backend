"""
Cover Letter Editor Agent

This agent refines and polishes the cover letter content for optimal impact.
"""

try:
    import os
    # Try to use real Google ADK by default, fall back to mock for testing
    if os.getenv('USE_MOCK_ADK', 'false').lower() == 'true':
        raise ImportError("Mock ADK forced for testing")
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from google.genai import types
    print("✅ Using real Google ADK")
except ImportError:
    print("⚠️ Google ADK not available, using mock implementation")
    # Import mock implementation
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from mock_adk import LlmAgent, FunctionTool
    # Mock types module
    import types

    class MockGenerateContentConfig:
        def __init__(self, temperature=0.1, response_mime_type=None, response_schema=None):
            self.temperature = temperature
            self.response_mime_type = response_mime_type
            self.response_schema = response_schema

    types.GenerateContentConfig = MockGenerateContentConfig
    types.Content = type('Content', (), {
        '__init__': lambda self, role, parts: None
    })
    types.Part = type('Part', (), {
        '__init__': lambda self, text=None, inline_data=None: None
    })

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json


class EditedCoverLetter(BaseModel):
    """Schema for edited cover letter content"""
    opening_paragraph: str = Field(description="Polished opening paragraph")
    body_paragraphs: List[str] = Field(description="Refined body paragraphs")
    company_connection: Optional[str] = Field(description="Polished company connection paragraph")
    closing_paragraph: str = Field(description="Strong closing paragraph")
    tone: str = Field(description="Final tone used")
    word_count: int = Field(description="Total word count")
    ats_score: int = Field(description="Estimated ATS compatibility score (1-10)")


def create_cover_letter_editor_agent():
    """
    Create the cover letter editor agent that refines and polishes content.

    Returns:
        LlmAgent configured for cover letter editing
    """

    schema_string = EditedCoverLetter.model_json_schema()

    editor_agent = LlmAgent(
    model="gemini-2.5-pro", 
    name="cover_letter_editor_agent",
    description="Edit and polish cover letter content for clarity, tone, and ATS-friendliness",
    instruction=(
        "## Persona ##"
        "\nYou are an expert cover letter editor and career coach with deep knowledge of modern ATS systems and what makes a document compelling to hiring managers."

        "\n\n## Goal ##"
        "\nYour goal is to meticulously edit and polish a draft cover letter for clarity, impact, and ATS compatibility. You will then provide the refined content and an analysis in a structured JSON format."

        "\n\n## Tools ##"
        "\nYou have no tools. All necessary content will be provided directly in the input."

        "\n\n## Process ##"
        "\n1. **Analyze:** First, read the entire draft to understand its core message, narrative, and intended tone."
        "\n2. **Execute Edits:** Systematically review the draft against the 'Editing Checklist' below. Apply all rules to improve flow, strengthen verbs, and ensure every claim is impactful and concise."
        "\n3. **Finalize:** Perform a final quality check for spelling, grammar, and word count before formatting your final output."

        "\n\n## Editing Checklist ##"
        "\n- **Clarity & Impact:** Polish language for conciseness. Strengthen calls-to-action and value propositions. Remove generic or clichéd phrases. Ensure smooth transitions between paragraphs."
        "\n- **Content & Evidence:** Verify all claims are specific and backed by evidence. Ensure the opening and closing paragraphs are strong and engaging."
        "\n- **ATS Optimization:** Ensure relevant keywords are included naturally. The structure must be simple and easily parsable (no tables, columns, or complex formatting)."
        "\n- **Technical Quality:** Correct all spelling and grammar errors. Ensure the word count is appropriate (between 250-450 words)."
        "\n- **Tone:** Confirm the tone is consistent and matches one of the required types: professional, creative, enthusiastic, or formal."

        "\n\n## Output Instructions ##"
        "\nCRITICAL REQUIREMENT: Your final output MUST be a single, valid JSON object that strictly "
        "adheres to the following JSON schema. Do not include any other text, explanations, or "
        "markdown code fences. Your response must start with { and end with }."
        f"\n\n## REQUIRED JSON OUTPUT SCHEMA ##\n```json\n{schema_string}\n```"
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,  # Lower temperature for precise, consistent editing.
    ),
    output_schema=EditedCoverLetter,
    output_key="edited_content",
    tools=[],
    )

    return editor_agent


async def run_cover_letter_editing(
    editor_agent,
    draft_content: Dict[str, Any],
    analysis_outline: Dict[str, Any],
    session_service,
    session_id: str,
    user_id: str = "user_123"
):
    """
    Run the cover letter editing using the editor agent.

    Args:
        editor_agent: The configured editor agent
        draft_content: The draft content from the writer agent
        analysis_outline: The original analysis outline for reference
        session_service: ADK session service
        session_id: Session ID for the agent run
        user_id: User ID for the session

    Returns:
        Dict containing the edited content
    """

    from google.adk.runners import Runner

    # Create the session first
    session = await session_service.create_session(
        app_name="cover_letter_editing",
        user_id=user_id,
        session_id=session_id
    )

    runner = Runner(agent=editor_agent, session_service=session_service, app_name="cover_letter_editing")

    # Build the editing prompt
    prompt_parts = [
        "Edit and polish this cover letter draft:",
        f"Draft content: {json.dumps(draft_content, indent=2)}",
        f"Original analysis: {json.dumps(analysis_outline, indent=2)}",
        "\nFocus on clarity, impact, ATS-friendliness, and professional tone."
    ]

    content_parts = [
        types.Part(text="\n\n".join(prompt_parts))
    ]

    content = types.Content(
        role='user',
        parts=content_parts
    )

    editing_result = None
    def _try_parse_json(s: str):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        s2 = s.strip()
        if s2.startswith("```"):
            s2 = s2.strip('`')
            if s2.lower().startswith("json\n"):
                s2 = s2[5:]
        start = s2.find('{')
        end = s2.rfind('}')
        if start != -1 and end != -1 and end > start:
            cand = s2[start:end+1]
            try:
                return json.loads(cand)
            except json.JSONDecodeError:
                pass
        return None

    async for event in runner.run_async(new_message=content, session_id=session_id, user_id=user_id):
        if event.is_final_response() and event.content:
            if hasattr(event.content, 'parts') and event.content.parts:
                raw_text = event.content.parts[0].text.strip()
                parsed = _try_parse_json(raw_text)
                if parsed is not None:
                    editing_result = parsed
                    print("✅ Cover letter editing completed successfully")
                else:
                    print("❌ Failed to parse editing result: Invalid JSON after cleanup")
                    print(f"Raw response: {raw_text}")

    return editing_result
