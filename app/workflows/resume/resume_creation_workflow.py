import json
import logging
import uuid
from datetime import datetime
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
        # Generate JSON schema directly from the Pydantic model
        resume_schema = ResumeResponse.model_json_schema()
        
        # Clean the schema to be compatible with Google GenAI function calling
        cleaned_schema = _clean_schema_for_genai(resume_schema)

        # 3. Define function declaration using correct API
        extract_resume_function = types.FunctionDeclaration(
            name="extract_resume_info",
            description="Extracts information from a resume into a structured JSON object.",
            parameters=cleaned_schema
        )

        # 4. Create tool and model with correct SDK usage
        tool = types.Tool(function_declarations=[extract_resume_function])
        
        # Configure GenAI with API key if provided
        if api_key:
            genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-2.5-pro', tools=[tool])
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


def _prepare_resume_data_for_validation(resume_data: dict) -> dict:
    """Prepare resume data for Pydantic validation by setting required fields."""
    # Set defaults for required fields if not present
    if 'id' not in resume_data:
        resume_data['id'] = str(uuid.uuid4())
    
    if 'userId' not in resume_data:
        resume_data['userId'] = "00000000-0000-0000-0000-000000000000"  # System user for anonymous uploads
    
    if 'createdAt' not in resume_data:
        resume_data['createdAt'] = datetime.now()
    
    if 'updatedAt' not in resume_data:
        resume_data['updatedAt'] = datetime.now()
    
    return resume_data


def _clean_schema_for_genai(schema: dict) -> dict:
    """Clean Pydantic v2 JSON schema to be compatible with Google GenAI function calling."""
    import copy
    cleaned = copy.deepcopy(schema)
    
    # Remove required fields to make AI parsing more flexible
    if "required" in cleaned:
        cleaned["required"] = []
    
    # Remove Pydantic v2 specific fields that Google GenAI doesn't support
    for key in ["$defs", "additionalProperties", "title"]:
        if key in cleaned:
            del cleaned[key]
    
    # Recursively remove $ref references to $defs
    def remove_refs(obj):
        if isinstance(obj, dict):
            if "$ref" in obj and obj["$ref"].startswith("#/$defs/"):
                # Replace $ref with a simple string type
                return {"type": "string", "description": "Referenced type"}
            else:
                return {k: remove_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [remove_refs(item) for item in obj]
        else:
            return obj
    
    return remove_refs(cleaned)