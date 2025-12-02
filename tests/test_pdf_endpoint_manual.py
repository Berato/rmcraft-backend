#!/usr/bin/env python3
"""
Manual test runner for the PDF rendering endpoint
Run this after starting the server with: python main.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_designer_pdf_endpoint import test_data, test_render_pdfs_endpoint, test_render_pdfs_with_invalid_ids

if __name__ == "__main__":
    print("🚀 Running PDF endpoint integration test manually...")
    print("Make sure the server is running on http://localhost:8000")

    try:
        # Set up test data
        data = test_data()
        print(f"📋 Test data: {data}")

        # Run the main test
        test_render_pdfs_endpoint(data)

        # Run error handling test
        test_render_pdfs_with_invalid_ids()

        print("✅ All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()