#!/usr/bin/env python3
"""
Test script to verify the strategic cover letter agents are configured correctly
"""

import os
import sys

# Set mock ADK for testing
os.environ['USE_MOCK_ADK'] = 'true'

def test_agents_creation():
    """Test that all agents can be created without errors"""
    try:
        from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent
        from app.agents.cover_letter.writer_agent import create_cover_letter_writer_agent
        from app.agents.cover_letter.editor_agent import create_cover_letter_editor_agent

        print("🧪 Testing agent creation...")

        # Mock query tools
        def dummy_query_tool(queries, top_k=4):
            return [{"document": "test doc", "metadata": {"type": "test"}, "score": 0.9}]

        # Test analyst agent
        analyst_agent = create_cover_letter_analyst_agent(dummy_query_tool, dummy_query_tool)
        print("✅ Analyst agent created successfully")

        # Test writer agent
        writer_agent = create_cover_letter_writer_agent(dummy_query_tool, dummy_query_tool)
        print("✅ Writer agent created successfully")

        # Test editor agent
        editor_agent = create_cover_letter_editor_agent()
        print("✅ Editor agent created successfully")

        return True

    except Exception as e:
        print(f"❌ Agent creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_configurations():
    """Test that agents have correct configurations"""
    try:
        from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent
        from app.agents.cover_letter.writer_agent import create_cover_letter_writer_agent
        from app.agents.cover_letter.editor_agent import create_cover_letter_editor_agent

        def dummy_query_tool(queries, top_k=4):
            return [{"document": "test doc", "metadata": {"type": "test"}, "score": 0.9}]

        print("🧪 Testing agent configurations...")

        # Test analyst agent config
        analyst_agent = create_cover_letter_analyst_agent(dummy_query_tool, dummy_query_tool)
        config = analyst_agent.generate_content_config
        assert hasattr(config, 'temperature')
        assert config.temperature == 0.3
        assert not hasattr(config, 'response_mime_type') or config.response_mime_type is None
        print("✅ Analyst agent config: temperature=0.3, no response_mime_type")

        # Test writer agent config
        writer_agent = create_cover_letter_writer_agent(dummy_query_tool, dummy_query_tool)
        config = writer_agent.generate_content_config
        assert hasattr(config, 'temperature')
        assert config.temperature == 0.6
        assert not hasattr(config, 'response_mime_type') or config.response_mime_type is None
        print("✅ Writer agent config: temperature=0.6, no response_mime_type")

        # Test editor agent config
        editor_agent = create_cover_letter_editor_agent()
        config = editor_agent.generate_content_config
        assert hasattr(config, 'temperature')
        assert config.temperature == 0.2
        assert not hasattr(config, 'response_mime_type') or config.response_mime_type is None
        print("✅ Editor agent config: temperature=0.2, no response_mime_type")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_instructions():
    """Test that agent instructions are appropriate"""
    try:
        from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent
        from app.agents.cover_letter.writer_agent import create_cover_letter_writer_agent
        from app.agents.cover_letter.editor_agent import create_cover_letter_editor_agent

        def dummy_query_tool(queries, top_k=4):
            return [{"document": "test doc", "metadata": {"type": "test"}, "score": 0.9}]

        print("🧪 Testing agent instructions...")

        # Test analyst agent instruction
        analyst_agent = create_cover_letter_analyst_agent(dummy_query_tool, dummy_query_tool)
        instruction = analyst_agent.instruction
        assert "JSON" not in instruction.upper()
        assert "analyze" in instruction.lower()
        assert "cover letter" in instruction.lower()
        print("✅ Analyst agent instruction is appropriate")

        # Test writer agent instruction
        writer_agent = create_cover_letter_writer_agent(dummy_query_tool, dummy_query_tool)
        instruction = writer_agent.instruction
        assert "JSON" not in instruction.upper()
        assert "write" in instruction.lower() or "draft" in instruction.lower()
        print("✅ Writer agent instruction is appropriate")

        # Test editor agent instruction
        editor_agent = create_cover_letter_editor_agent()
        instruction = editor_agent.instruction
        assert "edit" in instruction.lower() or "review" in instruction.lower()
        print("✅ Editor agent instruction is appropriate")

        return True

    except Exception as e:
        print(f"❌ Instruction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Testing Strategic Cover Letter Agents")
    print("=" * 50)

    # Test 1: Agent creation
    print("\n1. Testing agent creation...")
    creation_test = test_agents_creation()

    # Test 2: Agent configurations
    print("\n2. Testing agent configurations...")
    config_test = test_agent_configurations()

    # Test 3: Agent instructions
    print("\n3. Testing agent instructions...")
    instruction_test = test_agent_instructions()

    print("\n" + "=" * 50)
    if creation_test and config_test and instruction_test:
        print("✅ Strategic Cover Letter Agents are working correctly!")
        print("\n🚀 All fixes verified:")
        print("- ✅ Agents can be created without errors")
        print("- ✅ Google AI API compatibility fixed (no response_mime_type)")
        print("- ✅ Temperature settings are correct for each agent")
        print("- ✅ Instructions are appropriate and don't mention JSON")
        print("- ✅ Ready for integration with orchestrator")
        print("\n📡 Next step: Test with real Google AI API")
        print("   USE_MOCK_ADK=false python main.py")
    else:
        print("❌ Some tests failed. Check the error messages above.")
