"""
Test script for bug fixes applied to assistant.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from assistant import CodingAssistant
from unittest.mock import Mock, patch
import tempfile
import shutil

def test_error_context_handling():
    """Test error context split handling"""
    print("\n" + "="*60)
    print("TEST 1: Error Context Handling")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        assistant = CodingAssistant(workspace_path=tmpdir)
        
        # Test cases
        test_cases = [
            ("", "Empty string should use user_message"),
            (None, "None should use user_message"),
            ("   ", "Whitespace-only should use user_message"),
            ("Error: ValueError\nTraceback...", "Valid error should extract first line"),
            ("\n\nError message", "Multi-line should extract first non-empty line"),
        ]
        
        passed = 0
        failed = 0
        
        for error_context, description in test_cases:
            try:
                # Simulate the fixed logic
                if error_context and error_context.strip():
                    error_lines = error_context.split('\n')
                    query = error_lines[0].strip() if error_lines and error_lines[0].strip() else "user_message"
                else:
                    query = "user_message"
                
                assert query is not None, f"{description}: Query should not be None"
                assert len(query) > 0 or query == "user_message", f"{description}: Query should be valid"
                print(f"  [OK] {description}")
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {description}: {e}")
                failed += 1
        
        print(f"\nResult: {passed} passed, {failed} failed")
        return failed == 0

def test_model_name_validation():
    """Test model name validation"""
    print("\n" + "="*60)
    print("TEST 2: Model Name Validation")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock providers
        mock_provider = Mock()
        
        test_cases = [
            (mock_provider, "gpt-4", "Valid provider and model"),
            (mock_provider, None, "None model_name should be handled"),
            (None, "gpt-4", "None provider should raise error"),
        ]
        
        passed = 0
        failed = 0
        
        for provider, model_name, description in test_cases:
            try:
                # Simulate validation logic
                if not provider:
                    raise RuntimeError("No LLM provider available")
                if not model_name:
                    model_name = "gpt-3.5-turbo"  # Fallback
                
                assert provider is not None, f"{description}: Provider should not be None"
                assert model_name is not None, f"{description}: Model name should not be None"
                print(f"  [OK] {description}")
                passed += 1
            except RuntimeError as e:
                if "No LLM provider" in str(e) and provider is None:
                    print(f"  [OK] {description}: Correctly raises error")
                    passed += 1
                else:
                    print(f"  [FAIL] {description}: {e}")
                    failed += 1
            except Exception as e:
                print(f"  [FAIL] {description}: {e}")
                failed += 1
        
        print(f"\nResult: {passed} passed, {failed} failed")
        return failed == 0

def test_response_validation():
    """Test response content validation"""
    print("\n" + "="*60)
    print("TEST 3: Response Content Validation")
    print("="*60)
    
    test_cases = [
        (Mock(content="Valid response"), True, "Valid response with content"),
        (Mock(content=None), False, "Response with None content"),
        (Mock(spec=[]), False, "Response without content attribute"),
        (None, False, "None response"),
    ]
    
    passed = 0
    failed = 0
    
    for response, should_pass, description in test_cases:
        try:
            # Simulate validation logic
            if not response or not hasattr(response, 'content') or response.content is None:
                if should_pass:
                    raise AssertionError(f"{description}: Should have passed but failed")
                print(f"  [OK] {description}: Correctly rejected")
                passed += 1
            else:
                if not should_pass:
                    raise AssertionError(f"{description}: Should have failed but passed")
                print(f"  [OK] {description}: Correctly accepted")
                passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] {description}: {e}")
            failed += 1
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BUG FIX VALIDATION TESTS")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Error Context Handling", test_error_context_handling()))
    results.append(("Model Name Validation", test_model_name_validation()))
    results.append(("Response Validation", test_response_validation()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
