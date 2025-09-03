import json
import logging
from typing import Optional, Any

try:
    import google.generativeai as genai
    from google.generativeai import types
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import Google GenAI SDK: {e}")
    raise

from app.schemas.ResumeSchemas import ResumeResponse

logger = logging.getLogger(__name__)

def parse_resume_text_with_genai(resume_text: str, api_key: Optional[str] = None) -> ResumeResponse:
    """Send raw resume text to Google Generative AI, ask for strict JSON that matches ResumeResponse,
    parse the JSON, validate with Pydantic, and return the ResumeResponse instance.

    This helper is defensive: it attempts to extract a JSON object if the model returns surrounding text.
    It does not mutate external state.
    """
    
    prompt = f"""
    Extract the following fields from the resume and return a single JSON object and nothing else.
    The JSON keys must be exactly: id, userId, name, summary, personalInfo, experience, education, skills, projects,
    jobDescription, jobProfileId, themeId, createdAt, updatedAt.
    Use ISO-8601 for timestamps or null. For any missing optional values, use null or empty arrays/objects.

    Resume text:
    {resume_text}
    """

    # Make a text completion / chat call using function calling with cleaned schema
    try:
        # Define a simplified schema compatible with Google GenAI
        # Based on ResumeResponse but simplified for function calling
        simple_resume_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Resume ID (leave null if not provided)"},
                "userId": {"type": "string", "description": "User ID (leave null if not provided)"},
                "name": {"type": "string", "description": "Resume name or title"},
                "summary": {"type": "string", "description": "Resume summary or professional summary"},
                "personalInfo": {
                    "type": "object",
                    "properties": {
                        "firstName": {"type": "string", "description": "First name"},
                        "lastName": {"type": "string", "description": "Last name"},
                        "email": {"type": "string", "description": "Email address"},
                        "phone": {"type": "string", "description": "Phone number"},
                        "location": {"type": "string", "description": "Location/address"},
                        "linkedin": {"type": "string", "description": "LinkedIn profile URL"},
                        "website": {"type": "string", "description": "Personal website URL"},
                        "title": {"type": "string", "description": "Professional title"},
                        "summary": {"type": "string", "description": "Personal summary"}
                    }
                },
                "experience": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "company": {"type": "string", "description": "Company name"},
                            "position": {"type": "string", "description": "Job position/title"},
                            "startDate": {"type": "string", "description": "Start date"},
                            "endDate": {"type": "string", "description": "End date"},
                            "responsibilities": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "Job responsibilities and duties"
                            }
                        }
                    }
                },
                "education": {
                    "type": "array", 
                    "items": {
                        "type": "object",
                        "properties": {
                            "institution": {"type": "string", "description": "Educational institution"},
                            "degree": {"type": "string", "description": "Degree obtained"},
                            "fieldOfStudy": {"type": "string", "description": "Field of study"},
                            "startDate": {"type": "string", "description": "Start date"},
                            "endDate": {"type": "string", "description": "End date or graduation date"},
                            "gpa": {"type": "string", "description": "GPA if mentioned"}
                        }
                    }
                },
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Skill name"},
                            "category": {"type": "string", "description": "Skill category (technical, soft, etc.)"},
                            "level": {"type": "string", "description": "Skill level if mentioned"}
                        }
                    }
                },
                "projects": {
                    "type": "array",
                    "items": {
                        "type": "object", 
                        "properties": {
                            "name": {"type": "string", "description": "Project name"},
                            "description": {"type": "string", "description": "Project description"},
                            "technologies": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "Technologies used"
                            },
                            "url": {"type": "string", "description": "Project URL or repository link"},
                            "startDate": {"type": "string", "description": "Project start date"},
                            "endDate": {"type": "string", "description": "Project end date"}
                        }
                    }
                },
                "jobDescription": {"type": "string", "description": "Target job description if mentioned"},
                "jobProfileId": {"type": "string", "description": "Job profile ID if applicable"},
                "themeId": {"type": "string", "description": "Resume theme ID if applicable"},
                "createdAt": {"type": "string", "description": "Creation timestamp (leave null if not provided)"},
                "updatedAt": {"type": "string", "description": "Update timestamp (leave null if not provided)"}
            },
            "required": []
        }

        # 3. Define function declaration using correct API
        extract_resume_function = types.FunctionDeclaration(
            name="extract_resume_info",
            description="Extracts information from a resume into a structured JSON object.",
            parameters=simple_resume_schema
        )

        # 4. Create tool and model with correct SDK usage
        tool = types.Tool(function_declarations=[extract_resume_function])
        
        # Configure GenAI with API key if provided
        if api_key:
            genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-1.5-pro', tools=[tool])

        # 5. Generate content with function calling
        response = model.generate_content(prompt)

        # 6. Extract the function call response
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    if function_call.name == "extract_resume_info":
                        # Convert args to dict and validate with Pydantic
                        parsed_data = dict(function_call.args)
                        
                        # Handle missing required fields and type conversions
                        parsed_data = _prepare_resume_data_for_validation(parsed_data)
                        
                        resume_obj = ResumeResponse.model_validate(parsed_data)
                        return resume_obj

        # Fallback: try to parse as regular text response
        response_text = response.text if hasattr(response, 'text') else str(response)
        logger.warning("No function call found, attempting to parse text response")
        
        # Try to extract JSON from the response text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end + 1]
            parsed_data = json.loads(json_str)
            
            # Handle missing required fields and type conversions
            parsed_data = _prepare_resume_data_for_validation(parsed_data)
            
            resume_obj = ResumeResponse.model_validate(parsed_data)
            return resume_obj

        raise ValueError("Could not extract valid JSON or function call from AI response")

    except Exception as e:
        logger.exception(f"GenAI request failed: {e}")
        raise


def _prepare_resume_data_for_validation(data: dict) -> dict:
    """
    Prepare the AI-extracted data for ResumeResponse validation by handling
    missing required fields and type conversions.
    """
    from datetime import datetime
    import uuid
    
    # Ensure required fields exist with defaults
    if not data.get('id'):
        data['id'] = str(uuid.uuid4())
    
    if not data.get('userId'):
        data['userId'] = str(uuid.uuid4())  # Generate a placeholder user ID
    
    if not data.get('name'):
        data['name'] = 'Extracted Resume'
    
    # Handle datetime fields - convert None or strings to datetime objects
    current_time = datetime.now()
    
    if not data.get('createdAt'):
        data['createdAt'] = current_time
    elif isinstance(data['createdAt'], str):
        try:
            from dateutil.parser import parse
            data['createdAt'] = parse(data['createdAt'])
        except:
            data['createdAt'] = current_time
    
    if not data.get('updatedAt'):
        data['updatedAt'] = current_time
    elif isinstance(data['updatedAt'], str):
        try:
            from dateutil.parser import parse
            data['updatedAt'] = parse(data['updatedAt'])
        except:
            data['updatedAt'] = current_time
    
    # Ensure other fields have appropriate defaults
    if data.get('summary') is None:
        data['summary'] = ""
    
    if data.get('personalInfo') is None:
        data['personalInfo'] = {}
    
    if data.get('experience') is None:
        data['experience'] = []
    
    if data.get('education') is None:
        data['education'] = []
    
    if data.get('skills') is None:
        data['skills'] = []
    
    if data.get('projects') is None:
        data['projects'] = []
    
    return data