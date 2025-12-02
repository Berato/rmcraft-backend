"""
Test script for the theme triage endpoint
"""
import requests
import sys

def test_triage_endpoint():
    """Test the triage endpoint with a real PDF and theme ID"""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/themes/triage/68ee81489e0ef528b3f453c7"
    
    # PDF file path
    pdf_path = "/Users/berato/Downloads/triage.pdf"
    
    print("=" * 60)
    print("Testing Theme Triage Endpoint")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"PDF: {pdf_path}")
    print(f"Theme ID: 68ee81489e0ef528b3f453c7")
    print()
    
    try:
        # Open and send the file
        with open(pdf_path, 'rb') as pdf_file:
            files = {
                'resume_pdf': ('triage.pdf', pdf_file, 'application/pdf')
            }
            data = {
                'max_retries': '1'
            }
            
            print("Sending request...")
            response = requests.post(url, files=files, data=data, timeout=300)
            
            print(f"\n{'=' * 60}")
            print(f"Response Status: {response.status_code}")
            print(f"{'=' * 60}")
            
            if response.status_code == 200:
                print("✅ SUCCESS!")
                result = response.json()
                print("\nResponse Data:")
                print(f"Status: {result.get('status')}")
                print(f"Message: {result.get('message')}")
                
                data = result.get('data', {})
                print(f"\nWorkflow Results:")
                print(f"  Success: {data.get('success')}")
                print(f"  Attempts: {data.get('attempts')}")
                print(f"  Max Retries: {data.get('max_retries')}")
                print(f"  Theme ID: {data.get('theme_id')}")
                print(f"  Theme Name: {data.get('theme_name')}")
                
                if 'results' in data:
                    results = data['results']
                    print(f"\n  Workflow Details:")
                    print(f"    Attempt: {results.get('attempt')}")
                    
                    if 'original_issues' in results:
                        issues = results['original_issues']
                        if 'resume_triage_analysis' in issues:
                            analysis = issues['resume_triage_analysis']
                            print(f"\n    Resume Triage Analysis:")
                            print(f"      Overall: {analysis.get('overall_assessment', 'N/A')[:100]}...")
                            if 'issues' in analysis:
                                print(f"      Issues Found: {len(analysis['issues'])}")
                                for i, issue in enumerate(analysis['issues'][:3], 1):
                                    print(f"        {i}. [{issue.get('severity')}] {issue.get('issue_description', 'N/A')[:80]}...")
                        
                        if 'resume_code_update' in issues:
                            update = issues['resume_code_update']
                            print(f"\n    Resume Code Update:")
                            print(f"      Fixes Applied: {len(update.get('fixes_applied', []))}")
                            for i, fix in enumerate(update.get('fixes_applied', [])[:3], 1):
                                print(f"        {i}. {fix[:80]}...")
                    
                    if 'new_pdfs' in results:
                        pdfs = results['new_pdfs']
                        print(f"\n    New PDFs Generated:")
                        if 'resume' in pdfs:
                            print(f"      Resume: {pdfs['resume'].get('cloudinary_url', 'N/A')}")
                        if 'cover_letter' in pdfs:
                            print(f"      Cover Letter: {pdfs['cover_letter'].get('cloudinary_url', 'N/A')}")
                    
                    if 'verification' in results:
                        verification = results['verification']
                        print(f"\n    Verification:")
                        print(f"      All Issues Resolved: {verification.get('all_issues_resolved')}")
                        print(f"      Recommendation: {verification.get('recommendation')}")
                        if verification.get('remaining_issues'):
                            print(f"      Remaining Issues: {len(verification['remaining_issues'])}")
                
                return 0
            
            elif response.status_code == 206:
                print("⚠️ PARTIAL SUCCESS (issues remain)")
                print(response.json())
                return 0
            
            else:
                print(f"❌ ERROR: {response.status_code}")
                try:
                    error_detail = response.json()
                    print("\nError Details:")
                    print(error_detail)
                except:
                    print("\nRaw Response:")
                    print(response.text)
                return 1
                
    except FileNotFoundError:
        print(f"❌ ERROR: PDF file not found at {pdf_path}")
        return 1
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to the server. Is it running?")
        print("   Try: uvicorn main:app --reload")
        return 1
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out (>300 seconds)")
        return 1
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_triage_endpoint())
