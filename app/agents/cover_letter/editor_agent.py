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

    editor_agent = LlmAgent(
        model="gemini-2.5-flash",
        name="cover_letter_editor_agent",
        description="Edit and polish cover letter content for clarity, tone, and ATS-friendliness",
        instruction=(
            "You are an expert cover letter editor with deep knowledge of ATS systems and hiring practices. "
            "Your task is to refine the draft cover letter content for maximum impact while ensuring ATS compatibility."
            "\n\nEDITING TASKS:"
            "\n1. Polish language for clarity, conciseness, and impact"
            "\n2. Ensure consistent professional tone throughout"
            "\n3. Verify all claims are specific and backed by evidence"
            "\n4. Optimize for ATS systems (avoid complex formatting, use standard fonts implicitly)"
            "\n5. Check word count is appropriate (250-450 words total)"
            "\n6. Strengthen calls-to-action and value propositions"
            "\n7. Remove any generic or clichéd phrases"
            "\n8. Ensure smooth transitions between paragraphs"
            "\n\nATS OPTIMIZATION:"
            "\n- Use standard section headers if needed"
            "\n- Include relevant keywords naturally"
            "\n- Avoid tables, columns, or complex formatting"
            "\n- Use common file formats (implied in final output)"
            "\n- Ensure readable text structure"
            "\n\nQUALITY CHECKS:"
            "\n- No spelling or grammar errors"
            "\n- Professional yet personable tone"
            "\n- Specific examples and achievements"
            "\n- Clear value proposition"
            "\n- Strong opening and closing"
            "\n\nReturn the polished content with word count and ATS compatibility assessment."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2  # Low temperature for consistent editing
        ),
        output_schema=EditedCoverLetter,
        output_key="edited_content",
        tools=[],  # Editor doesn't need external tools, works with provided content
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

    async for event in runner.run_async(new_message=content, session_id=session_id, user_id=user_id):
        if event.is_final_response() and event.content:
            if hasattr(event.content, 'parts') and event.content.parts:
                raw_text = event.content.parts[0].text.strip()
                try:
                    editing_result = json.loads(raw_text)
                    print("✅ Cover letter editing completed successfully")
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse editing result: {e}")
                    print(f"Raw response: {raw_text}")

    return editing_result
