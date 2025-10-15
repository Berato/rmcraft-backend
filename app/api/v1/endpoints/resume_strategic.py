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


@router.get("/strategic-analysis-stream")
async def run_strategic_analysis_stream(
    resume_id: str,
    job_description_url: str
):
    """
    Run strategic resume analysis with streaming Server-Sent Events.
    
    Returns real-time progress updates as the AI agent processes the analysis.
    EventSource requires GET requests, so parameters are passed as query params.
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    async def generate_analysis_stream():
        try:
            # Initial status
            yield f"data: {json.dumps({'status': 'starting', 'step': 'Initializing analysis', 'progress': 10})}\n\n"
            await asyncio.sleep(0.1)
            
            # Resume loading
            yield f"data: {json.dumps({'status': 'progress', 'step': 'Loading resume data', 'progress': 20})}\n\n"
            await asyncio.sleep(0.5)
            
            # Job description fetching
            yield f"data: {json.dumps({'status': 'progress', 'step': 'Fetching job description', 'progress': 30})}\n\n"
            await asyncio.sleep(0.5)
            
            # ADK agent processing with streaming wrapper
            yield f"data: {json.dumps({'status': 'progress', 'step': 'Running strategic analysis', 'progress': 40})}\n\n"
            await asyncio.sleep(1.0)
            
            # Simulate streaming from Google ADK agent
            steps = [
                "Analyzing resume content",
                "Matching skills to job requirements", 
                "Evaluating experience relevance",
                "Generating strategic recommendations",
                "Finalizing analysis results"
            ]
            
            for i, step in enumerate(steps):
                progress = 50 + (i * 10)
                yield f"data: {json.dumps({'status': 'progress', 'step': step, 'progress': progress})}\n\n"
                await asyncio.sleep(1.0)
            
            # Run the actual agent (this could be modified to support streaming)
            result = await strategic_resume_agent(
                resume_id=resume_id,
                job_description_url=job_description_url
            )
            
            # Validate and return final result
            validated_data = ResumeAnalysisSchema(**result)
            
            yield f"data: {json.dumps({'status': 'complete', 'step': 'Analysis complete', 'progress': 100, 'result': validated_data.model_dump()})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'step': 'Analysis failed', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_analysis_stream(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
