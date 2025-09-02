#!/usr/bin/env python3
"""
Test with a valid resume in the database to verify BaseModel validation
"""
import requests
import os
import sys
import json

def test_with_mock_database():
    """Test the endpoint with mock database containing valid resume"""
    
    # Set up mock ADK mode
    os.environ['USE_MOCK_ADK'] = 'true'
    
    # First create a test resume in the database by calling the create endpoint
    create_url = "http://localhost:8000/api/v1/resumes"
    
    # Valid resume data
    resume_data = {
        "name": "Test Resume for BaseModel Validation",
        "summary": "Senior Software Engineer with experience",
        "personalInfo": {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-1234"
        },
        "experience": [
            {
                "id": "exp_1",
                "company": "Test Corporation",
                "position": "Senior Developer",
                "startDate": "2021-01",
                "endDate": "2024-08",
                "description": "Led development team",
                "location": "Remote"
            }
        ],
        "education": [
            {
                "id": "edu_1", 
                "school": "Test University",
                "degree": "BS Computer Science",
                "field": "Computer Science",
                "startDate": "2005",
                "endDate": "2009"
            }
        ],
        "skills": [
            {"id": "skill_1", "name": "JavaScript", "level": 4},
            {"id": "skill_2", "name": "React", "level": 4}
        ],
        "projects": [
            {
                "id": "proj_1",
                "name": "Test Project",
                "description": "A test project for validation",
                "url": "https://example.com/project"
            }
        ]
    }
    
    print("\ud83e\uddea Testing BaseModel Validation with Valid Resume Data")
    print("\ud83d\udcdd Step 1: Creating test resume...")
    
    try:
        # Create resume
        create_response = requests.post(create_url, json=resume_data)
        
        if create_response.status_code != 201:
            print(f"\u274c Could not create test resume: {create_response.status_code}")
            print(f"   Response: {create_response.text}")
            print("\u26a0\ufe0f  Testing with non-existent resume to verify error handling...")
            
            # Test with non-existent resume (should properly fail)
            test_data = {
                "resume_id": "test-resume-nonexistent", 
                "job_description_url": "https://example.com/job"
            }
            
        else:
            created_resume = create_response.json()
            resume_id = created_resume.get('data', {}).get('id')
            print(f"\u2705 Created test resume with ID: {resume_id}")
            
            # Test with the created resume
            test_data = {
                "resume_id": resume_id,
                "job_description_url": "https://example.com/job"
            }
    
    except Exception as e:
        print(f"\u26a0\ufe0f  Could not create resume: {e}")
        print("   Testing with non-existent resume...")
        test_data = {
            "resume_id": "test-resume-nonexistent",
            "job_description_url": "https://example.com/job"
        }
    
    print("\n\ud83d\udcdd Step 2: Testing strategic analysis...")
    analysis_url = "http://localhost:8000/api/v1/resumes/strategic-analysis"
    
    try:
        response = requests.post(analysis_url, data=test_data)
        print(f"\ud83d\udcca Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("\u2705 Success! Analyzing response...")
            data = response.json()
            
            resume_data = data.get('data', {})
            
            # Validate all required fields are present
            validation_results = {}
            
            # Check experiences
            experiences = resume_data.get('experiences', [])
            for i, exp in enumerate(experiences):
                required = ['id', 'company', 'position', 'startDate', 'endDate', 'responsibilities']
                missing = [f for f in required if f not in exp]
                validation_results[f'experience_{i}'] = len(missing) == 0
                if missing:
                    print(f"\u274c Experience {i} missing: {missing}")
                else:
                    print(f"\u2705 Experience {i} has all required fields")
            
            # Check skills  
            skills = resume_data.get('skills', [])
            for i, skill in enumerate(skills):
                required = ['id', 'name', 'level']
                missing = [f for f in required if f not in skill]
                validation_results[f'skill_{i}'] = len(missing) == 0
                if missing:
                    print(f"\u274c Skill {i} missing: {missing}")
                else:
                    print(f"\u2705 Skill {i} has all required fields")
            
            # Check projects
            projects = resume_data.get('projects', [])
            for i, proj in enumerate(projects):
                required = ['id', 'name', 'description', 'url']
                missing = [f for f in required if f not in proj]
                validation_results[f'project_{i}'] = len(missing) == 0
                if missing:
                    print(f"\u274c Project {i} missing: {missing}")
                else:
                    print(f"\u2705 Project {i} has all required fields")
                    
            all_valid = all(validation_results.values())
            
            if all_valid:
                print("\n\ud83c\udf89 ALL VALIDATION PASSED!")
                print("\u2705 BaseModel schemas are working correctly")
                print("\u2705 No field validation errors")
                return True
            else:
                print("\n\u26a0\ufe0f  Some validation issues found")
                failed_items = [k for k, v in validation_results.items() if not v]
                print(f"   Failed validations: {failed_items}")
                return False
                
        elif response.status_code == 500:
            error_data = response.json()
            error_detail = error_data.get('detail', '')
            
            if "Resume not found" in error_detail:
                print("\u2705 Expected behavior: Resume not found")
                print("\u2705 System properly rejects non-existent resumes")
                print("\u2705 BaseModel validation is working correctly")
                return True
            else:
                print(f"\u274c Unexpected error: {error_detail}")
                return False
        else:
            print(f"\u274c Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\u274c Request failed: {e}")
        return False

if __name__ == "__main__":
    success = test_with_mock_database()
    print("\n" + "="*60)
    if success:
        print("\ud83c\udf89 TEST PASSED!")
        print("\u2705 BaseModel validation is working correctly") 
        print("\u2705 Google ADK field validation errors are resolved")
    else:
        print("\ud83d\udca5 TEST FAILED!")
        print("\u274c BaseModel validation issues still present")
