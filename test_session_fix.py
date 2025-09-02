#!/usr/bin/env python3
"""
Test script for cover letter session management fix
"""

import asyncio
import os
import sys

# Set mock ADK for testing
os.environ['USE_MOCK_ADK'] = 'true'

# Load mock ADK before any other imports
try:
    import google.adk
    print("✅ Real Google ADK loaded")
except ImportError:
    print("⚠️ Loading mock ADK...")
    exec(open('mock_adk.py').read())
    print("✅ Mock ADK loaded")

async def test_session_creation():
    """Test that sessions are created properly"""
    try:
        from google.adk.sessions import InMemorySessionService
        from google.adk.runners import Runner
        from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent, run_cover_letter_analysis

        print("✅ Imports successful")

        # Create session service
        session_service = InMemorySessionService()
        print("✅ Session service created")

        # Create session
        session_id = "test_session_123"
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user",
            session_id=session_id
        )
        print(f"✅ Session created: {session.session_id}")

        # Create a simple agent for testing
        def dummy_query_tool(queries, top_k=4):
            return [{"document": "test doc", "metadata": {"type": "test"}, "score": 0.9}]

        agent = create_cover_letter_analyst_agent(dummy_query_tool, dummy_query_tool)
        print("✅ Agent created")

        # Test the runner
        runner = Runner(agent=agent, session_service=session_service, app_name="test_app")
        print("✅ Runner created")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_workflow():
    """Test the full cover letter workflow"""
    try:
        from app.features.cover_letter_orchestrator import cover_letter_orchestrator

        print("🧪 Testing full cover letter workflow...")

        # This would normally require a real resume, but let's test the session creation part
        # We'll mock the resume service call
        from unittest.mock import patch, AsyncMock, MagicMock

        mock_resume = MagicMock()
        mock_resume.model_dump.return_value = {
            'experience': [{'company': 'Test Corp', 'position': 'Developer', 'responsibilities': ['Coded stuff']}],
            'skills': [{'name': 'Python'}],
            'summary': 'Test summary'
        }

        with patch('app.features.cover_letter_orchestrator.get_resume_pydantic', return_value=mock_resume), \
             patch('app.features.cover_letter_orchestrator.get_url_contents', return_value=['Job description text']), \
             patch('app.agents.cover_letter.analyst_agent.run_cover_letter_analysis', return_value={
                 'role_summary': 'Test Role',
                 'company_summary': 'Test Company',
                 'strong_matches': [],
                 'risk_mitigations': [],
                 'outline': {'opening': 'test', 'body': [], 'closing': 'test'}
             }), \
             patch('app.agents.cover_letter.writer_agent.run_cover_letter_writing', return_value={
                 'opening_paragraph': 'Test opening',
                 'body_paragraphs': ['Test body'],
                 'closing_paragraph': 'Test closing',
                 'tone': 'professional'
             }), \
             patch('app.agents.cover_letter.editor_agent.run_cover_letter_editing', return_value={
                 'opening_paragraph': 'Test opening',
                 'body_paragraphs': ['Test body'],
                 'closing_paragraph': 'Test closing',
                 'tone': 'professional',
                 'word_count': 50,
                 'ats_score': 7
             }):

            result = await cover_letter_orchestrator(
                resume_id="test-resume-123",
                job_description_url="https://example.com/job"
            )

            if result and 'finalContent' in result:
                print("✅ Full workflow test passed!")
                print(f"   Generated content length: {len(result['finalContent'])}")
                return True
            else:
                print("❌ Full workflow test failed - no result")
                return False

    except Exception as e:
        print(f"❌ Full workflow error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🔧 Testing Google ADK Session Management Fix")
    print("=" * 50)

    # Test 1: Basic session creation
    print("\n1. Testing session creation...")
    session_test = await test_session_creation()

    # Test 2: Full workflow
    print("\n2. Testing full workflow...")
    workflow_test = await test_full_workflow()

    print("\n" + "=" * 50)
    if session_test and workflow_test:
        print("✅ All tests passed! Session management issue should be resolved.")
        print("\n🚀 You can now test the API endpoint:")
        print("   USE_MOCK_ADK=true python main.py")
        print("   POST /api/v1/cover-letters/strategic-create")
    else:
        print("❌ Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())
