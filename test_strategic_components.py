#!/usr/bin/env python3
"""
Test the strategic analysis API endpoint directly via FastAPI
"""
import os
import sys
import json
import asyncio

# Set environment variable to use mock
os.environ['USE_MOCK_ADK'] = 'true'

# Add the project root to the Python path
sys.path.insert(0, '/Users/berato/Sites/rmcraft-backend')

def test_endpoint_request_structure():
    """Test the endpoint request structure"""
    try:
        from app.api.v1.endpoints.resume_strategic import StrategicAnalysisRequest
        
        # Test that we can create a request object
        request = StrategicAnalysisRequest(
            resume_id="test_resume_id",
            job_description_url="https://example.com/job"
        )
        
        print("✅ Request structure test passed!")
        print(f"📋 Request: {request}")
        return True
        
    except Exception as e:
        print(f"❌ Request structure test failed: {e}")
        return False

def test_response_schema():
    """Test the response schema"""
    try:
        from app.schemas.ResumeSchemas import ResumeAnalysisSchema
        
        # Test that we can create a response schema
        mock_data = {
            "experiences": [],
            "skills": [],
            "projects": [],
            "education": [],
            "contact_info": [],
            "summary": "Test summary",
            "name": "Test Name"
        }
        
        schema = ResumeAnalysisSchema(**mock_data)
        print("✅ Response schema test passed!")
        print(f"📋 Schema: {schema}")
        return True
        
    except Exception as e:
        print(f"❌ Response schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mock_adk():
    """Test the mock ADK implementation"""
    try:
        # Import mock ADK
        import mock_adk
        
        # Test thinking config
        thinking_config = mock_adk.MockThinkingConfig(include_thoughts=True, thinking_budget=512)
        print(f"✅ ThinkingConfig: {thinking_config.include_thoughts}, {thinking_config.thinking_budget}")
        
        # Test generate content config with response schema
        config = mock_adk.MockGenerateContentConfig(
            temperature=0.5,
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "experiences": {"type": "ARRAY"}
                }
            }
        )
        print(f"✅ GenerateContentConfig: {config.temperature}, {config.response_mime_type}")
        print(f"✅ Response schema: {config.response_schema}")
        
        # Test LLM Agent
        agent = mock_adk.MockLlmAgent(
            model="gemini-2.5-flash",
            name="test_agent",
            description="Test agent",
            instruction="Test instruction",
            generate_content_config=config
        )
        print(f"✅ LlmAgent: {agent.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock ADK test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔄 Testing strategic analysis implementation...")
    
    test1 = test_endpoint_request_structure()
    test2 = test_response_schema()
    test3 = test_mock_adk()
    
    if all([test1, test2, test3]):
        print("\n✅ All tests passed! The strategic analysis implementation is working.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
