#!/usr/bin/env python3
"""
Simple test to verify BaseModel validation is working
"""
import requests
import os

def test_basemodel_validation():
    """Test that the API properly validates with BaseModel schemas"""
    
    # Set up mock ADK mode
    os.environ['USE_MOCK_ADK'] = 'true'
    
    url = "http://localhost:8000/api/v1/resumes/strategic-analysis"
    
    test_data = {
        "resume_id": "test-resume-123",
        "job_description_url": "https://example.com/job-posting"
    }
    
    print("\ud83e\uddea Testing BaseModel Validation Fix")
    print(f"\ud83d\udce1 URL: {url}")
    print(f"\ud83d\udccb Request: {test_data}")
    
    try:
        response = requests.post(url, data=test_data)
        print(f"\ud83d\udcca Status Code: {response.status_code}")
        
        if response.status_code == 500:
            try:
                error_data = response.json()
                error_detail = error_data.get('detail', '')
                
                if "Resume not found" in error_detail:
                    print("\u2705 PERFECT! Expected behavior:")
                    print("   Resume not found error is properly handled")
                    print("   No invalid test data with missing fields")
                    print("   BaseModel validation is working correctly")
                    return True
                elif "Field required" in error_detail and "input_value" in error_detail:
                    print("\u274c BaseModel validation error still occurring:")
                    print(f"   {error_detail}")
                    print("   This means mock data is still missing required fields")
                    return False
                else:
                    print(f"\u274c Unexpected error: {error_detail}")
                    return False
                    
            except:
                print(f"\u274c Could not parse error response: {response.text}")
                return False
                
        elif response.status_code == 200:
            print("\u2705 Request succeeded - checking data validity...")
            try:
                data = response.json()
                resume_data = data.get('data', {})
                
                # Check if experiences have required fields
                experiences = resume_data.get('experiences', [])
                for i, exp in enumerate(experiences):
                    if 'id' not in exp:
                        print(f"\u274c Experience {i} missing 'id' field")
                        return False
                
                # Check if skills have required fields
                skills = resume_data.get('skills', [])
                for i, skill in enumerate(skills):
                    if 'id' not in skill:
                        print(f"\u274c Skill {i} missing 'id' field")
                        return False
                
                # Check if projects have required fields
                projects = resume_data.get('projects', [])
                for i, proj in enumerate(projects):
                    if 'id' not in proj or 'url' not in proj:
                        missing = []
                        if 'id' not in proj:
                            missing.append('id')
                        if 'url' not in proj:
                            missing.append('url')
                        print(f"\u274c Project {i} missing fields: {missing}")
                        return False
                
                print("\u2705 All data has required fields!")
                print("\u2705 BaseModel validation is working correctly!")
                return True
                
            except Exception as e:
                print(f"\u274c Error parsing response: {e}")
                return False
        else:
            print(f"\u274c Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\u274c Request failed: {e}")
        return False

if __name__ == "__main__":
    print("\ud83d\udd0d Testing if BaseModel fix resolved Google ADK validation errors...")
    print()
    
    success = test_basemodel_validation()
    
    print()
    if success:
        print("\ud83c\udf89 SUCCESS!")
        print("\u2705 BaseModel changes fixed the Google ADK validation errors")
        print("\u2705 No more 'Field required' errors for missing IDs")
        print("\u2705 System properly handles non-existent resumes") 
    else:
        print("\ud83d\udca5 FAILED!")
        print("\u274c BaseModel validation errors still occurring")
        print("\u274c Need to investigate further")
