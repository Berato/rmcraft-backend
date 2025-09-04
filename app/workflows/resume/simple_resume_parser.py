"""
Simple, clean resume parser that just works.
No complex schemas, no function calling, just direct AI text parsing.
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any
import google.generativeai as genai
from app.schemas.ResumeSchemas import ResumeResponse


def parse_resume_simple(resume_text: str, user_id: str = None) -> ResumeResponse:
    """
    Simple resume parser that uses direct text generation instead of function calling.
    Much cleaner and more reliable than complex schema approaches.
    """
    
    # Simple, direct prompt
    prompt = f"""
    Please extract information from this resume and return it as a clean JSON object.
    
    Return ONLY valid JSON with these fields:
    - name: Resume/person name
    - summary: Professional summary
    - personalInfo: object with firstName, lastName, email, phone, location, etc.
    - experience: array of job experiences with company, position, startDate, endDate, responsibilities
    - education: array of education with institution, degree, fieldOfStudy, startDate, endDate
    - skills: array of skills with name, category, level
    - projects: array of projects with name, description, technologies, url, dates
    
    Make sure the JSON is valid and parseable. Use empty arrays [] for missing sections.
    
    Resume text:
    {resume_text}
    
    JSON:
    """
    
    try:
        # Simple text generation - no function calling complexity
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Find JSON boundaries
        if '{' in response_text and '}' in response_text:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_str = response_text[start:end]
            
            # Parse the JSON
            resume_data = json.loads(json_str)
            
            # Add required database fields
            resume_data['id'] = str(uuid.uuid4())
            resume_data['userId'] = user_id or "00000000-0000-0000-0000-000000000000"
            resume_data['createdAt'] = datetime.now()
            resume_data['updatedAt'] = datetime.now()
            
            # Ensure required nested structures exist and add missing IDs
            if 'personalInfo' not in resume_data or not resume_data['personalInfo']:
                resume_data['personalInfo'] = {}
            if isinstance(resume_data['personalInfo'], dict) and 'id' not in resume_data['personalInfo']:
                resume_data['personalInfo']['id'] = str(uuid.uuid4())
            
            if 'experience' not in resume_data:
                resume_data['experience'] = []
            # Add IDs to experience items
            for exp in resume_data['experience']:
                if isinstance(exp, dict) and 'id' not in exp:
                    exp['id'] = str(uuid.uuid4())
            
            if 'education' not in resume_data:
                resume_data['education'] = []
            # Add IDs to education items
            for edu in resume_data['education']:
                if isinstance(edu, dict) and 'id' not in edu:
                    edu['id'] = str(uuid.uuid4())
            
            if 'skills' not in resume_data:
                resume_data['skills'] = []
            # Add IDs to skill items
            for skill in resume_data['skills']:
                if isinstance(skill, dict) and 'id' not in skill:
                    skill['id'] = str(uuid.uuid4())
            
            if 'projects' not in resume_data:
                resume_data['projects'] = []
            # Add IDs to project items
            for project in resume_data['projects']:
                if isinstance(project, dict) and 'id' not in project:
                    project['id'] = str(uuid.uuid4())
                
            # Validate with Pydantic
            return ResumeResponse.model_validate(resume_data)
            
        else:
            raise ValueError("No valid JSON found in AI response")
            
    except Exception as e:
        raise ValueError(f"Failed to parse resume: {str(e)}")
