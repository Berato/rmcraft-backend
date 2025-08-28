#!/usr/bin/env python3
"""
Quick test to verify the strategic resume endpoint works
"""

def test_endpoint_definition():
    """Test that the endpoint is properly defined"""
    try:
        from app.api.v1.endpoints.resumes import router
        
        # Check if the strategic-analysis route exists
        routes = [route.path for route in router.routes]
        print(f"Available routes: {routes}")
        
        strategic_route = next((route for route in router.routes if route.path == "/strategic-analysis"), None)
        if strategic_route:
            print("✅ Strategic analysis endpoint is properly defined")
            print(f"   Methods: {strategic_route.methods}")
            return True
        else:
            print("❌ Strategic analysis endpoint not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing endpoint definition: {e}")
        return False

def test_pydantic_schemas():
    """Test that the Pydantic schemas work"""
    try:
        from app.api.v1.endpoints.resumes import StrategicResumeRequest, StrategicResumeResponse
        
        # Test request schema
        request = StrategicResumeRequest(
            resume_id="test-123",
            job_description_url="https://example.com/job"
        )
        print(f"✅ Request schema works: {request.model_dump()}")
        
        # Test response schema  
        response = StrategicResumeResponse(
            status=200,
            message="Test message",
            data="Test data"
        )
        print(f"✅ Response schema works: {response.model_dump()}")
        return True
        
    except Exception as e:
        print(f"❌ Error testing schemas: {e}")
        return False

def test_strategic_agent_import():
    """Test that the strategic agent can be imported"""
    try:
        from app.agents.resume.strategic.strategic_resume_agent import strategic_resume_agent
        print("✅ Strategic resume agent imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing strategic agent: {e}")
        return False

if __name__ == "__main__":
    print("Testing Strategic Resume Analysis Setup...")
    print("=" * 50)
    
    tests = [
        ("Endpoint Definition", test_endpoint_definition),
        ("Pydantic Schemas", test_pydantic_schemas), 
        ("Strategic Agent Import", test_strategic_agent_import)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The endpoint is ready to use.")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
