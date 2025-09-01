#!/usr/bin/env python3
"""
Test script for strategic resume endpoint fixes
"""
import requests
import json
import time

def test_strategic_endpoint():
    url = 'http://127.0.0.1:8000/api/v1/resumes/strategic-analysis'
    data = {
        'resume_id': 'test_resume_123',
        'job_description_url': 'https://example.com/job'
    }

    try:
        print("🧪 Testing strategic resume endpoint...")
        response = requests.post(url, data=data, timeout=60)  # Use data for form fields

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Request successful!")

            # Check key fields in the response data
            response_data = result.get('data', {})
            experiences = response_data.get('experiences', [])
            skills = response_data.get('skills', {})
            projects = response_data.get('projects', [])
            summary = response_data.get('summary', '')

            print(f"📋 Experiences: {len(experiences)} items")
            print(f"🛠️  Skills: {len(skills.get('skills', []))} items")
            print(f"📁 Projects: {len(projects)} items")
            print(f"� Summary: {'✅ Present' if summary else '❌ Missing'}")

            return True
        else:
            print(f"❌ Request failed: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
        return False
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

if __name__ == "__main__":
    # Wait a moment for server to be ready
    time.sleep(2)
    success = test_strategic_endpoint()
    exit(0 if success else 1)
