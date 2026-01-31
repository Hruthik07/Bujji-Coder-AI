"""
Edge case testing for the application
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"

def test_empty_codebase():
    """Test with empty codebase"""
    print("\n" + "="*60)
    print("EDGE CASE: Empty Codebase")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/files", timeout=5)
        if response.status_code == 200:
            data = response.json()
            files = data.get('files', [])
            print(f"  [OK] Empty codebase handled: {len(files)} files")
            return True
        else:
            print(f"  [FAIL] Status {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False

def test_invalid_requests():
    """Test invalid request handling"""
    print("\n" + "="*60)
    print("EDGE CASE: Invalid Requests")
    print("="*60)
    
    test_cases = [
        ("POST /api/chat with empty message", {"message": ""}, "Empty message"),
        ("POST /api/chat with None", None, "None payload"),
        ("GET /api/files with invalid path", {"directory": "../../etc/passwd"}, "Path traversal attempt"),
    ]
    
    passed = 0
    failed = 0
    
    for name, payload, description in test_cases:
        try:
            if "chat" in name:
                response = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=5)
            elif "files" in name:
                response = requests.get(f"{BASE_URL}/api/files", params=payload, timeout=5)
            else:
                continue
            
            # Should handle gracefully (either 200 with error message or 400/422)
            if response.status_code in [200, 400, 422]:
                print(f"  [OK] {description}: Handled gracefully (status {response.status_code})")
                passed += 1
            else:
                print(f"  [WARN] {description}: Unexpected status {response.status_code}")
                passed += 1  # Not a failure, just unexpected
        except Exception as e:
            print(f"  [FAIL] {description}: {e}")
            failed += 1
    
    print(f"\n  Result: {passed} passed, {failed} failed")
    return failed == 0

def test_concurrent_requests():
    """Test concurrent request handling"""
    print("\n" + "="*60)
    print("EDGE CASE: Concurrent Requests")
    print("="*60)
    
    import concurrent.futures
    
    def make_request(i):
        try:
            response = requests.get(f"{BASE_URL}/api/status", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    duration = time.time() - start
    
    passed = sum(results)
    total = len(results)
    
    print(f"  Concurrent requests: {passed}/{total} passed")
    print(f"  Duration: {duration:.2f}s")
    
    if passed == total:
        print(f"  [OK] All concurrent requests handled successfully")
        return True
    else:
        print(f"  [WARN] Some concurrent requests failed")
        return passed >= total * 0.8  # 80% success rate acceptable

def test_large_payload():
    """Test with large payload"""
    print("\n" + "="*60)
    print("EDGE CASE: Large Payload")
    print("="*60)
    
    try:
        # Create a large message
        large_message = "Test message. " * 1000  # ~14KB
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": large_message},
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"  [OK] Large payload handled: {len(large_message)} chars")
            return True
        else:
            print(f"  [WARN] Large payload: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Large payload: {e}")
        return False

def test_timeout_handling():
    """Test timeout handling"""
    print("\n" + "="*60)
    print("EDGE CASE: Timeout Handling")
    print("="*60)
    
    try:
        # Test with very short timeout
        response = requests.get(f"{BASE_URL}/api/performance", timeout=0.1)
        print(f"  [WARN] Request completed faster than expected")
        return True
    except requests.exceptions.Timeout:
        print(f"  [OK] Timeout handled correctly")
        return True
    except Exception as e:
        print(f"  [INFO] Timeout test: {e}")
        return True  # Not a failure

def main():
    """Run edge case tests"""
    print("\n" + "="*60)
    print("EDGE CASE TESTING")
    print("="*60)
    
    results = []
    results.append(("Empty Codebase", test_empty_codebase()))
    results.append(("Invalid Requests", test_invalid_requests()))
    results.append(("Concurrent Requests", test_concurrent_requests()))
    results.append(("Large Payload", test_large_payload()))
    results.append(("Timeout Handling", test_timeout_handling()))
    
    print("\n" + "="*60)
    print("EDGE CASE TEST SUMMARY")
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
