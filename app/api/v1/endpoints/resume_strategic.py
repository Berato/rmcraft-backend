from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.resume.strategic.strategic_resume_agent import strategic_resume_agent
from app.schemas.ResumeSchemas import ResumeAnalysisSchema

router = APIRouter()

class StrategicAnalysisRequest(BaseModel):
    resume_id: str
    job_description_url: str

class StrategicAnalysisResponse(BaseModel):
    status: int
    message: str
    data: ResumeAnalysisSchema

@router.post("/strategic-analysis", response_model=StrategicAnalysisResponse)
async def run_strategic_analysis(request: StrategicAnalysisRequest):
    """
    Run strategic resume analysis with thinking mode.
    """
    try:
        result = await strategic_resume_agent(
            resume_id=request.resume_id,
            job_description_url=request.job_description_url
        )
        
        # The agent now returns a dictionary that should match the schema
        # We can re-validate it here before sending the response
        validated_data = ResumeAnalysisSchema(**result)

        return StrategicAnalysisResponse(
            status=200,
            message="Strategic analysis completed successfully",
            data=validated_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
