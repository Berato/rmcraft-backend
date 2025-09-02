from google.adk.agents import SequentialAgent, ParallelAgent
from app.agents.theme_agents import theme_analyst_agent, resume_theme_agent, cover_letter_theme_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import uuid
# Import your actual database service functions and schemas
# from app.services.theme_service import create_theme, create_theme_package
# from app.schemas.ThemeSchemas import Theme, ThemePackage, ThemeType

# Step 1: Define the parallel execution step for the two theme creators
parallel_theme_creation = ParallelAgent(
    name="parallel_theme_creation",
    description="Generates resume and cover letter themes concurrently.",
    sub_agents=[
        resume_theme_agent,
        cover_letter_theme_agent
    ]
)

# Step 2: Define the full sequential workflow
full_theme_workflow = SequentialAgent(
    name="full_theme_workflow",
    description="Analyzes a design request and then generates a complete theme package.",
    sub_agents=[
        theme_analyst_agent,
        parallel_theme_creation
    ]
)

async def create_and_save_theme(design_prompt: str, image_data: bytes, image_mime_type: str, user_id: str):
    """
    Orchestrates the end-to-end process of generating and saving a new theme.
    """
    # 1. Set up ADK Runner
    session_service = InMemorySessionService()
    session_id = uuid.uuid4().hex
    await session_service.create_session(session_id=session_id, app_name="theme_generator", user_id=user_id)  # Create the session
    runner = Runner(agent=full_theme_workflow, session_service=session_service, app_name="theme_generator")

    # 2. Construct Multimodal Input
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=design_prompt),
            types.Part(inline_data=types.Blob(mime_type=image_mime_type, data=image_data))
        ]
    )
    
    # 3. Execute the Workflow and Collect Results
    final_response = {}
    async for event in runner.run_async(new_message=content, session_id=session_id, user_id=user_id):
        print(f"🔍 Event: {type(event).__name__}, is_final: {event.is_final_response()}")
        
        if hasattr(event, 'author'):
            print(f"   author: {event.author}")
        if hasattr(event, 'content') and event.content and event.content.parts:
            print(f"   content: {str(event.content.parts[0].text)[:200]}...")
        
        # For ADK agents with output_schema, the final response is JSON in content
        if event.is_final_response() and hasattr(event, 'content') and event.content and event.content.parts:
            response_text = event.content.parts[0].text
            print(f"✅ Final response received from {event.author}: {response_text[:100]}...")
            
            # Try to parse as JSON since agents have output_schema
            try:
                import json
                response_data = json.loads(response_text)
                
                # Map agent names to output keys based on the agent definitions
                if event.author == "theme_analyst_agent":
                    final_response["theme_brief"] = response_data
                    print(f"✅ Stored theme_brief: {list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)}")
                elif event.author == "resume_theme_agent":
                    final_response["resume_theme"] = response_data
                    print(f"✅ Stored resume_theme: {list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)}")
                elif event.author == "cover_letter_theme_agent":
                    final_response["cover_letter_theme"] = response_data
                    print(f"✅ Stored cover_letter_theme: {list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON from {event.author}: {e}")
                print(f"   Raw response: {response_text}")
                # Store as raw text fallback
                if event.author == "theme_analyst_agent":
                    final_response["theme_brief"] = {"raw_response": response_text}
                elif event.author == "resume_theme_agent":
                    final_response["resume_theme"] = {"raw_response": response_text}
                elif event.author == "cover_letter_theme_agent":
                    final_response["cover_letter_theme"] = {"raw_response": response_text}

    # 4. Package the Theme and Save to Database
    print(f"📋 Final response keys: {list(final_response.keys())}")
    print(f"📋 Final response: {final_response}")
    
    theme_brief = final_response.get("theme_brief", {})
    resume_theme_data = final_response.get("resume_theme", {})
    cover_letter_theme_data = final_response.get("cover_letter_theme", {})

    print(f"📋 theme_brief: {bool(theme_brief)}")
    print(f"📋 resume_theme_data: {bool(resume_theme_data)}")
    print(f"📋 cover_letter_theme_data: {bool(cover_letter_theme_data)}")

    if not all([theme_brief, resume_theme_data, cover_letter_theme_data]):
        raise Exception("Theme generation failed. One or more agents did not produce output.")

    # Create individual Theme records for resume and cover letter
    # This assumes a service function `create_theme` that returns the created Theme object
    
    # new_resume_theme = await create_theme(
    #     name=f"{theme_brief.get('name')} - Resume",
    #     description=theme_brief.get('description'),
    #     type=ThemeType.RESUME,
    #     template=resume_theme_data.get('template'),
    #     styles=resume_theme_data.get('styles')
    # )
    #
    # new_cover_letter_theme = await create_theme(
    #     name=f"{theme_brief.get('name')} - Cover Letter",
    #     description=theme_brief.get('description'),
    #     type=ThemeType.COVER_LETTER,
    #     template=cover_letter_theme_data.get('template'),
    #     styles=cover_letter_theme_data.get('styles')
    # )

    # Create the ThemePackage that links them
    # This assumes a service function `create_theme_package`
    
    # saved_theme_package = await create_theme_package(
    #     name=theme_brief.get('name'),
    #     description=theme_brief.get('description'),
    #     resume_template_id=new_resume_theme.id,
    #     cover_letter_template_id=new_cover_letter_theme.id
    # )
    #
    # return saved_theme_package
    
    # For now, we'll return a dictionary matching your ThemePackage schema
    print("✅ Theme package created successfully.")
    return {
        "name": theme_brief.get('name'),
        "description": theme_brief.get('description'),
        "resumeTemplate": resume_theme_data,
        "coverLetterTemplate": cover_letter_theme_data,
    }
