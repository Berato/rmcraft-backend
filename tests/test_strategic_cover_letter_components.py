"""
Comprehensive tests for strategic cover letter components
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json


@pytest.mark.asyncio
async def test_analyst_agent_creation():
    """Test creation of cover letter analyst agent"""
    from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent

    # Mock query tools
    resume_query_tool = MagicMock()
    job_query_tool = MagicMock()

    agent = create_cover_letter_analyst_agent(resume_query_tool, job_query_tool)

    # Check that agent was created with expected properties
    assert agent is not None
    assert hasattr(agent, 'name')
    assert agent.name == "cover_letter_analyst_agent"


@pytest.mark.asyncio
async def test_writer_agent_creation():
    """Test creation of cover letter writer agent"""
    from app.agents.cover_letter.writer_agent import create_cover_letter_writer_agent

    # Mock query tools
    resume_query_tool = MagicMock()
    job_query_tool = MagicMock()

    agent = create_cover_letter_writer_agent(resume_query_tool, job_query_tool)

    # Check that agent was created with expected properties
    assert agent is not None
    assert hasattr(agent, 'name')
    assert agent.name == "cover_letter_writer_agent"


def test_editor_agent_creation():
    """Test creation of cover letter editor agent"""
    from app.agents.cover_letter.editor_agent import create_cover_letter_editor_agent

    agent = create_cover_letter_editor_agent()

    # Check that agent was created with expected properties
    assert agent is not None
    assert hasattr(agent, 'name')
    assert agent.name == "cover_letter_editor_agent"


@pytest.mark.asyncio
async def test_orchestrator_with_mock_data():
    """Test cover letter orchestrator with mocked dependencies"""
    from app.features.cover_letter_orchestrator import cover_letter_orchestrator

    # Mock the dependencies
    mock_resume = MagicMock()
    mock_resume.model_dump.return_value = {
        "experience": [{"company": "Test Corp", "position": "Developer", "responsibilities": ["Developed software"]}],
        "skills": [{"name": "Python"}],
        "summary": "Experienced developer"
    }

    with patch('app.features.cover_letter_orchestrator.get_resume_pydantic', return_value=mock_resume), \
         patch('app.features.cover_letter_orchestrator.get_url_contents', return_value=["Job description content"]), \
         patch('app.agents.cover_letter.analyst_agent.run_cover_letter_analysis', return_value={
             "role_summary": "Software Developer",
             "company_summary": "Tech Company",
             "strong_matches": [{"skill": "Python", "evidence": "Used in projects"}],
             "risk_mitigations": [],
             "outline": {"opening": "Hook", "body": ["Para1"], "closing": "CTA"}
         }), \
         patch('app.agents.cover_letter.writer_agent.run_cover_letter_writing', return_value={
             "opening_paragraph": "Dear Hiring Manager,",
             "body_paragraphs": ["I am excited to apply."],
             "closing_paragraph": "Thank you."
         }), \
         patch('app.agents.cover_letter.editor_agent.run_cover_letter_editing', return_value={
             "opening_paragraph": "Dear Hiring Manager,",
             "body_paragraphs": ["I am excited to apply."],
             "closing_paragraph": "Thank you.",
             "tone": "professional",
             "word_count": 50,
             "ats_score": 8
         }):

        result = await cover_letter_orchestrator(
            resume_id="test-resume-123",
            job_description_url="https://example.com/job",
            optional_prompt=None
        )

        # Verify the result structure
        assert result is not None
        assert "finalContent" in result
        assert "openingParagraph" in result
        assert "bodyParagraphs" in result
        assert "closingParagraph" in result
        assert result["resumeId"] == "test-resume-123"


def test_process_resume_for_chroma():
    """Test processing resume data for ChromaDB"""
    from app.features.cover_letter_orchestrator import process_resume_for_chroma

    resume_data = {
        "experience": [
            {
                "company": "Test Corp",
                "position": "Developer",
                "responsibilities": ["Developed software", "Built APIs"]
            }
        ],
        "projects": [
            {
                "id": "proj1",
                "name": "Test Project",
                "description": "A test project"
            }
        ],
        "skills": [{"name": "Python"}, {"name": "JavaScript"}],
        "summary": "Experienced developer"
    }

    documents, metadatas, ids = process_resume_for_chroma(resume_data)

    # Check that we got data
    assert len(documents) > 0
    assert len(metadatas) > 0
    assert len(ids) > 0

    # Check that IDs are unique
    assert len(ids) == len(set(ids))

    # Check metadata structure
    for meta in metadatas:
        assert "type" in meta


@pytest.mark.asyncio
async def test_orchestrator_error_handling():
    """Test error handling in orchestrator"""
    from app.features.cover_letter_orchestrator import cover_letter_orchestrator
    from app.services.resume_service import get_resume_pydantic

    # Test with non-existent resume
    with patch('app.features.cover_letter_orchestrator.get_resume_pydantic', return_value=None):
        with pytest.raises(ValueError, match="Resume not found"):
            await cover_letter_orchestrator(
                resume_id="non-existent",
                job_description_url="https://example.com/job"
            )


def test_api_request_validation():
    """Test API request model validation"""
    from app.api.v1.endpoints.cover_letters import StrategicCoverLetterRequest

    # Valid request
    valid_request = StrategicCoverLetterRequest(
        resumeId="test-123",
        jobDescriptionUrl="https://example.com/job",
        prompt="Make it enthusiastic"
    )
    assert valid_request.resumeId == "test-123"
    assert valid_request.jobDescriptionUrl == "https://example.com/job"
    assert valid_request.prompt == "Make it enthusiastic"

    # Request without optional prompt
    minimal_request = StrategicCoverLetterRequest(
        resumeId="test-123",
        jobDescriptionUrl="https://example.com/job"
    )
    assert minimal_request.prompt is None
