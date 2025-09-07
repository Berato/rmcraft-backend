from google.adk.agents import SequentialAgent, ParallelAgent
from app.agents.theme_agents import theme_analyst_agent, resume_theme_agent, cover_letter_theme_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import uuid
# Import your actual database service functions and schemas
from app.services.theme_service import save_theme_from_agents

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
    
    # Use strict validation + persistence wrapper (Beanie-backed)
    saved_theme_package = await save_theme_from_agents(final_response=final_response)
    print("✅ Theme package saved to database successfully (validated).")
    return saved_theme_package
