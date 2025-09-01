# Mock the google.adk module
import sys
import json
from types import ModuleType
from typing import List
from unittest.mock import Mock

# Create mock classes first
class MockThinkingConfig:
    def __init__(self, include_thoughts: bool = False, thinking_budget: int = 0):
        self.include_thoughts = include_thoughts
        self.thinking_budget = thinking_budget


class MockGenerateContentConfig:
    def __init__(self, temperature: float = 0.1, response_mime_type: str = "application/json"):
        self.temperature = temperature
        self.response_mime_type = response_mime_type


class MockPlanner:
    def __init__(self, thinking_config=None):
        self.thinking_config = thinking_config or MockThinkingConfig()


class MockBuiltInPlanner(MockPlanner):
    def __init__(self, thinking_config=None):
        super().__init__(thinking_config)


class MockContent:
    def __init__(self, role: str, parts: List):
        self.role = role
        self.parts = parts


class MockPart:
    def __init__(self, text: str = None, inline_data=None):
        self.text = text
        self.inline_data = inline_data


class MockBlob:
    def __init__(self, mime_type: str, data: bytes):
        self.mime_type = mime_type
        self.data = data


class MockSession:
    def __init__(self, app_name: str, user_id: str, session_id: str):
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id


class MockSessionService:
    async def create_session(self, app_name: str, user_id: str, session_id: str):
        return MockSession(app_name, user_id, session_id)


class MockEvent:
    def __init__(self, is_final: bool = True, content=None, output_key=None, output=None):
        self._is_final = is_final
        self.content = content
        self.output_key = output_key
        self.output = output

    def is_final_response(self):
        return self._is_final


class MockLlmAgent:
    def __init__(self, model: str, name: str, description: str, instruction: str,
                 generate_content_config=None, output_key=None, output_schema=None,
                 planner=None, tools=None):
        self.model = model
        self.name = name
        self.description = description
        self.instruction = instruction
        self.generate_content_config = generate_content_config
        self.output_key = output_key
        self.output_schema = output_schema
        self.planner = planner
        self.tools = tools or []

    async def run_async(self, content, session_id, user_id):
        """Mock implementation that returns predefined responses"""
        # Mock responses for different agents
        mock_responses = {
            "experience_agent": {
                "experiences": [
                    {
                        "id": "exp_1",
                        "company": "Tech Corp",
                        "position": "Senior Engineer",
                        "startDate": "2020-01",
                        "endDate": "2023-01",
                        "responsibilities": ["Led development team", "Implemented new features"]
                    }
                ]
            },
            "skills_agent": {
                "skills": [
                    {"id": "skill_1", "name": "Python", "level": 5},
                    {"id": "skill_2", "name": "JavaScript", "level": 4}
                ],
                "additional_skills": ["Docker", "AWS"]
            },
            "projects_agent": {
                "projects": [
                    {
                        "id": "proj_1",
                        "name": "E-commerce Platform",
                        "description": "Built scalable e-commerce platform",
                        "url": "https://example.com"
                    }
                ]
            },
            "summary_agent": {
                "summary": "Experienced software engineer with 5+ years in web development, specializing in Python and JavaScript."
            },
            "brief_agent": {
                "layout_description": "Modern two-column resume layout",
                "color_palette": {"primary": "#1a365d", "accent": "#3182ce"},
                "google_fonts": ["Inter", "Roboto Slab"],
                "design_prompt_for_developer": "Create a clean, modern resume with two columns"
            },
            "designer_agent": {
                "jinja_template": "<html><body><h1>{{ summary }}</h1></body></html>",
                "css_styles": "body { font-family: Inter; color: #1a365d; }"
            }
        }

        # Return mock response for this agent
        if self.name in mock_responses:
            response_data = mock_responses[self.name]
            event = MockEvent(
                is_final=True,
                content=MockContent(role="assistant", parts=[MockPart(text=json.dumps(response_data))]),
                output_key=self.output_key,
                output=response_data
            )
            yield event


class MockParallelAgent:
    def __init__(self, name: str, description: str, sub_agents: List):
        self.name = name
        self.description = description
        self.sub_agents = sub_agents

    async def run_async(self, content, session_id, user_id):
        """Mock implementation that runs all sub-agents"""
        for agent in self.sub_agents:
            async for event in agent.run_async(content, session_id, user_id):
                yield event


class MockSequentialAgent:
    def __init__(self, name: str, description: str, sub_agents: List):
        self.name = name
        self.description = description
        self.sub_agents = sub_agents

    async def run_async(self, content, session_id, user_id):
        """Mock implementation that runs all sub-agents in sequence"""
        for agent in self.sub_agents:
            async for event in agent.run_async(content, session_id, user_id):
                yield event


class MockRunner:
    def __init__(self, agent, session_service, app_name: str):
        self.agent = agent
        self.session_service = session_service
        self.app_name = app_name

    async def run_async(self, new_message, session_id: str, user_id: str):
        """Mock implementation that delegates to the agent"""
        async for event in self.agent.run_async(new_message, session_id, user_id):
            yield event


# Create the mock modules
mock_adk = ModuleType('google.adk')
mock_adk.agents = ModuleType('agents')
mock_adk.agents.LlmAgent = MockLlmAgent
mock_adk.agents.ParallelAgent = MockParallelAgent
mock_adk.agents.SequentialAgent = MockSequentialAgent
mock_adk.runners = ModuleType('runners')
mock_adk.runners.Runner = MockRunner
mock_adk.sessions = ModuleType('sessions')
mock_adk.sessions.InMemorySessionService = MockSessionService
mock_adk.tools = ModuleType('tools')
mock_adk.tools.FunctionTool = Mock
mock_adk.tools.google_search = Mock()
mock_adk.tools.agent_tool = ModuleType('agent_tool')
mock_adk.tools.agent_tool.AgentTool = Mock
mock_adk.planners = ModuleType('planners')
mock_adk.planners.BuiltInPlanner = MockBuiltInPlanner

# Also create google.genai mock
mock_genai = ModuleType('google.genai')
mock_genai.types = ModuleType('types')
mock_genai.types.GenerateContentConfig = MockGenerateContentConfig
mock_genai.types.ThinkingConfig = MockThinkingConfig
mock_genai.types.Content = MockContent
mock_genai.types.Part = MockPart
mock_genai.types.Blob = MockBlob

# Add to sys.modules
sys.modules['google.adk'] = mock_adk
sys.modules['google.adk.agents'] = mock_adk.agents
sys.modules['google.adk.runners'] = mock_adk.runners
sys.modules['google.adk.sessions'] = mock_adk.sessions
sys.modules['google.adk.tools'] = mock_adk.tools
sys.modules['google.adk.planners'] = mock_adk.planners
sys.modules['google.genai'] = mock_genai
sys.modules['google.genai.types'] = mock_genai.types

# Export classes at module level for direct import
ParallelAgent = MockParallelAgent
SequentialAgent = MockSequentialAgent
LlmAgent = MockLlmAgent
Runner = MockRunner
InMemorySessionService = MockSessionService
FunctionTool = Mock
google_search = Mock()
agent_tool = Mock()
BuiltInPlanner = MockBuiltInPlanner

print("✅ Mock ADK implementation loaded successfully")
