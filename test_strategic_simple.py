#!/usr/bin/env python3
"""
Simple test for strategic resume agent without database dependencies
"""
import os
import sys
import asyncio
import json

# Set environment variable to use mock
os.environ['USE_MOCK_ADK'] = 'true'

# Add the project root to the Python path
sys.path.insert(0, '/Users/berato/Sites/rmcraft-backend')

async def test_strategic_endpoint():
    """Test the strategic analysis endpoint directly"""
    try:
        # Mock the dependencies we need
        from unittest.mock import Mock, patch
        
        # Mock the resume service
        mock_resume = Mock()
        mock_resume.education = []
        mock_resume.personalInfo = {
            "firstName": "Wilson",
            "lastName": "Berato",
            "email": "wilson.berato@gmail.com"
        }
        mock_resume.model_dump.return_value = {
            "summary": "Senior Software Engineer with 13+ years of experience",
            "experience": [
                {
                    "company": "Target Corporation",
                    "position": "Senior Software Engineer",
                    "startDate": "2021-01",
                    "endDate": "2024-08",
                    "responsibilities": ["Led front-end development"]
                }
            ],
            "projects": [
                {
                    "name": "Konjure",
                    "description": "Internal sales platform"
                }
            ],
            "skills": [
                {"name": "TypeScript"},
                {"name": "React"}
            ],
            "education": [],
            "personalInfo": {
                "firstName": "Wilson",
                "lastName": "Berato",
                "email": "wilson.berato@gmail.com"
            }
        }
        
        with patch('app.services.resume_service.get_resume_pydantic', return_value=mock_resume):
            with patch('app.tools.get_url_contents.get_url_contents', return_value=["Job description content"]):
                from app.agents.resume.strategic.strategic_resume_agent import strategic_resume_agent
                
                print("🔄 Running strategic analysis...")
                result = await strategic_resume_agent('test_resume_id', 'https://example.com/job')
                
                print("✅ Strategic analysis completed!")
                print("📋 Result structure:")
                print(json.dumps(result, indent=2))
                
                # Check if the result has the expected structure
                required_fields = ['experiences', 'skills', 'projects', 'education', 'contact_info', 'summary', 'name']
                missing_fields = [field for field in required_fields if field not in result]
                
                if missing_fields:
                    print(f"⚠️ Missing fields: {missing_fields}")
                else:
                    print("✅ All required fields present!")
                    
                return result
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_strategic_endpoint())
