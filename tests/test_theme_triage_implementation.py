"""
Test the Theme Triage Workflow Implementation

This test verifies that:
1. All schemas are properly defined
2. All agents can be created
3. The workflow orchestrator can be imported
4. The API endpoint is properly registered
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_schemas():
    """Test that all triage schemas are properly defined"""
    print("\n" + "="*60)
    print("Testing Triage Schemas...")
    print("="*60)
    
    try:
        from app.schemas.triage_schemas import (
            IssueIdentification,
            TriageAnalysisOutput,
            ThemeCodeUpdate,
            VerificationResult,
            ThemeTriageRequest,
            ThemeTriageResponse
        )
        
        # Test IssueIdentification
        issue = IssueIdentification(
            issue_description="Test issue",
            severity="major",
            code_location="test.css",
            suggested_fix="Fix the test"
        )
        print(f"✅ IssueIdentification schema works: {issue.severity}")
        
        # Test TriageAnalysisOutput
        analysis = TriageAnalysisOutput(
            issues=[issue],
            overall_assessment="Test assessment"
        )
        print(f"✅ TriageAnalysisOutput schema works: {len(analysis.issues)} issues")
        
        # Test ThemeCodeUpdate
        update = ThemeCodeUpdate(
            template="<html>test</html>",
            styles="body { margin: 0; }",
            fixes_applied=["Fixed spacing"]
        )
        print(f"✅ ThemeCodeUpdate schema works: {len(update.fixes_applied)} fixes")
        
        # Test VerificationResult
        verification = VerificationResult(
            all_issues_resolved=True,
            remaining_issues=[],
            new_issues=[],
            recommendation="approve"
        )
        print(f"✅ VerificationResult schema works: {verification.recommendation}")
        
        # Test ThemeTriageRequest
        request = ThemeTriageRequest(
            theme_id="test123",
            max_retries=2
        )
        print(f"✅ ThemeTriageRequest schema works: max_retries={request.max_retries}")
        
        # Test ThemeTriageResponse
        response = ThemeTriageResponse(
            status=200,
            message="Test completed",
            data={"test": "data"}
        )
        print(f"✅ ThemeTriageResponse schema works: status={response.status}")
        
        print("\n✅ All schemas passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agents():
    """Test that all triage agents can be created"""
    print("\n" + "="*60)
    print("Testing Triage Agents...")
    print("="*60)
    
    try:
        # Set mock mode for testing
        os.environ['USE_MOCK_ADK'] = 'true'
        
        from app.agents.triage.triage_agents import (
            create_resume_triage_agent,
            create_cover_letter_triage_agent,
            create_resume_engineer_agent,
            create_cover_letter_engineer_agent,
            create_verification_agent
        )
        
        # Create each agent
        resume_triage = create_resume_triage_agent()
        print(f"✅ Resume triage agent created: {resume_triage.name}")
        
        cover_triage = create_cover_letter_triage_agent()
        print(f"✅ Cover letter triage agent created: {cover_triage.name}")
        
        resume_engineer = create_resume_engineer_agent()
        print(f"✅ Resume engineer agent created: {resume_engineer.name}")
        
        cover_engineer = create_cover_letter_engineer_agent()
        print(f"✅ Cover letter engineer agent created: {cover_engineer.name}")
        
        verification = create_verification_agent()
        print(f"✅ Verification agent created: {verification.name}")
        
        print("\n✅ All agents created successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_import():
    """Test that the workflow orchestrator can be imported"""
    print("\n" + "="*60)
    print("Testing Workflow Orchestrator Import...")
    print("="*60)
    
    try:
        from app.workflows.theme_triage_workflow import execute_theme_triage_workflow
        
        print(f"✅ Workflow orchestrator imported: {execute_theme_triage_workflow.__name__}")
        print(f"   Docstring: {execute_theme_triage_workflow.__doc__[:100]}...")
        
        print("\n✅ Workflow orchestrator import successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_endpoint_registration():
    """Test that the API endpoint is properly registered"""
    print("\n" + "="*60)
    print("Testing API Endpoint Registration...")
    print("="*60)
    
    try:
        from app.api.v1.endpoints.themes import router
        
        # Find the triage endpoint
        triage_route = None
        for route in router.routes:
            if hasattr(route, 'path') and 'triage' in route.path:
                triage_route = route
                break
        
        if triage_route:
            print(f"✅ Triage endpoint found: {triage_route.path}")
            print(f"   Methods: {triage_route.methods}")
            print(f"   Name: {triage_route.name}")
        else:
            print("❌ Triage endpoint not found in router")
            print("\nAvailable routes:")
            for route in router.routes:
                if hasattr(route, 'path'):
                    print(f"  - {route.path}")
            return False
        
        print("\n✅ API endpoint registration successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Endpoint registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_composition():
    """Test that agents can be composed into sequential and parallel workflows"""
    print("\n" + "="*60)
    print("Testing Agent Composition...")
    print("="*60)
    
    try:
        os.environ['USE_MOCK_ADK'] = 'true'
        
        from app.agents.triage.triage_agents import (
            create_resume_triage_agent,
            create_resume_engineer_agent
        )
        
        # Import composition classes
        try:
            from google.adk.agents import SequentialAgent, ParallelAgent
        except ImportError:
            from mock_adk import SequentialAgent, ParallelAgent
        
        # Create a sequential workflow
        resume_triage = create_resume_triage_agent()
        resume_engineer = create_resume_engineer_agent()
        
        sequential_workflow = SequentialAgent(
            name="test_sequential",
            description="Test sequential workflow",
            sub_agents=[resume_triage, resume_engineer]
        )
        print(f"✅ Sequential workflow created: {sequential_workflow.name}")
        print(f"   Sub-agents: {len(sequential_workflow.sub_agents)}")
        
        # Create a parallel workflow
        parallel_workflow = ParallelAgent(
            name="test_parallel",
            description="Test parallel workflow",
            sub_agents=[sequential_workflow]
        )
        print(f"✅ Parallel workflow created: {parallel_workflow.name}")
        print(f"   Sub-agents: {len(parallel_workflow.sub_agents)}")
        
        print("\n✅ Agent composition successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Agent composition test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 THEME TRIAGE IMPLEMENTATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Schemas", test_schemas()))
    results.append(("Agents", test_agents()))
    results.append(("Workflow Import", test_workflow_import()))
    results.append(("Endpoint Registration", test_endpoint_registration()))
    results.append(("Agent Composition", test_agent_composition()))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Implementation is complete.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
