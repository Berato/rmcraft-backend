def get_resume_data_schema():
    return {
        "name": "get_resume_data",
        "description": "Extract resume data for strategic analysis",
        "parameters": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "enum": ["experiences", "skills", "projects"]},
                "criteria": {"type": "string"}
            },
            "required": ["section", "criteria"]
        }
    }
