"""
Test script to verify the strategic resume analysis endpoint works
"""
import requests
import json

# Test data
form_data = {
    "resume_id": "test-resume-123",
    "job_description_url": "https://example.com/job-posting"
}

# No files needed for the simplified endpoint
files = None

# Test endpoint URL (adjust port if needed)
url = "http://localhost:8000/api/v1/resumes/strategic-analysis"

def test_endpoint():
    """Test the strategic resume analysis endpoint"""
    try:
        # Test the simplified endpoint without file uploads
        response = requests.post(url, data=form_data, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("\u2705 Endpoint is working correctly!")
        else:
            print(f"\u274c Endpoint returned error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\u274c Cannot connect to server. Make sure the FastAPI server is running on localhost:8000")
    except Exception as e:
        print(f"\u274c Error testing endpoint: {e}")

if __name__ == "__main__":
    print("Testing Strategic Resume Analysis Endpoint...")
    test_endpoint()
