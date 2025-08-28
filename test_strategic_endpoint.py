"""
Test script to verify the strategic resume analysis endpoint works
"""
import requests
import json

# Test data
test_data = {
    "resume_id": "test-resume-123",
    "job_description_url": "https://example.com/job-posting"
}

# Test endpoint URL (adjust port if needed)
url = "http://localhost:8000/api/v1/resumes/strategic-analysis"

def test_endpoint():
    """Test the strategic resume analysis endpoint"""
    try:
        response = requests.post(url, json=test_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Endpoint is working correctly!")
        else:
            print(f"❌ Endpoint returned error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the FastAPI server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")

if __name__ == "__main__":
    print("Testing Strategic Resume Analysis Endpoint...")
    test_endpoint()
