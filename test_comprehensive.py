"""
Comprehensive test suite for the application
Tests all major features and functionality
"""
import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8001"
TIMEOUT = 30

results = {
    "tests_passed": 0,
    "tests_failed": 0,
    "errors": [],
    "performance": {},
    "timestamp": datetime.now().isoformat()
}

def log_test(name, passed, duration=None, error=None):
    """Log test result"""
    status = "[OK]" if passed else "[FAIL]"
    duration_str = f" ({duration:.2f}s)" if duration else ""
    print(f"{status} {name}{duration_str}")
    
    if passed:
        results["tests_passed"] += 1
    else:
        results["tests_failed"] += 1
        if error:
            results["errors"].append({"test": name, "error": str(error)})

def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("HEALTH CHECK TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Health check endpoint", True, duration)
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Assistant Ready: {data.get('assistant_ready', False)}")
            return True
        else:
            log_test("Health check endpoint", False, duration, f"Status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        log_test("Health check endpoint", False, None, "Cannot connect to server")
        print("   [WARN] Backend server not running. Start it with: python web/backend/app.py")
        return False
    except Exception as e:
        log_test("Health check endpoint", False, time.time() - start, str(e))
        return False

def test_status_endpoint():
    """Test status endpoint"""
    print("\n" + "="*60)
    print("STATUS ENDPOINT TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Status endpoint", True, duration)
            print(f"   Assistant Ready: {data.get('assistant_ready', False)}")
            print(f"   RAG Indexed: {data.get('rag_indexed', False)}")
            print(f"   Model: {data.get('model', 'N/A')}")
            print(f"   RAG Chunks: {data.get('rag_chunks', 0)}")
            return True
        else:
            log_test("Status endpoint", False, duration, f"Status {response.status_code}")
            return False
    except Exception as e:
        log_test("Status endpoint", False, time.time() - start, str(e))
        return False

def test_file_operations():
    """Test file operations"""
    print("\n" + "="*60)
    print("FILE OPERATIONS TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/files", timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("List files", True, duration)
            print(f"   Files found: {len(data.get('files', []))}")
            return True
        else:
            log_test("List files", False, duration, f"Status {response.status_code}")
            return False
    except Exception as e:
        log_test("List files", False, time.time() - start, str(e))
        return False

def test_rag_indexing():
    """Test RAG indexing"""
    print("\n" + "="*60)
    print("RAG INDEXING TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/api/index", json={"force": False}, timeout=60)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("RAG indexing", True, duration)
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Chunks: {data.get('chunks_indexed', 0)}")
            return True
        else:
            log_test("RAG indexing", False, duration, f"Status {response.status_code}")
            return False
    except Exception as e:
        log_test("RAG indexing", False, time.time() - start, str(e))
        return False

def test_chat_functionality():
    """Test chat functionality"""
    print("\n" + "="*60)
    print("CHAT FUNCTIONALITY TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "Hello, can you help me?"},
            timeout=30
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Chat endpoint", True, duration)
            print(f"   Response received: {len(data.get('response', ''))} chars")
            return True
        else:
            log_test("Chat endpoint", False, duration, f"Status {response.status_code}")
            return False
    except Exception as e:
        log_test("Chat endpoint", False, time.time() - start, str(e))
        return False

def test_performance_endpoint():
    """Test performance endpoint"""
    print("\n" + "="*60)
    print("PERFORMANCE ENDPOINT TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/performance", timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Performance endpoint", True, duration)
            print(f"   Response time: {data.get('avg_response_time', 0):.2f}s")
            print(f"   Total requests: {data.get('total_requests', 0)}")
            return True
        else:
            log_test("Performance endpoint", False, duration, f"Status {response.status_code}")
            return False
    except Exception as e:
        log_test("Performance endpoint", False, time.time() - start, str(e))
        return False

def test_git_integration():
    """Test Git integration"""
    print("\n" + "="*60)
    print("GIT INTEGRATION TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/git/status", timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Git status", True, duration)
            print(f"   Is repo: {data.get('is_repo', False)}")
            return True
        else:
            log_test("Git status", False, duration, f"Status {response.status_code}")
            return False
    except Exception as e:
        log_test("Git status", False, time.time() - start, str(e))
        return False

def test_rules_engine():
    """Test rules engine"""
    print("\n" + "="*60)
    print("RULES ENGINE TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/rules", timeout=5)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Rules endpoint", True, duration)
            print(f"   Rules loaded: {data.get('has_rules', False)}")
            return True
        else:
            log_test("Rules endpoint", False, duration, f"Status {response.status_code}")
            return False
    except Exception as e:
        log_test("Rules endpoint", False, time.time() - start, str(e))
        return False

def main():
    """Run all comprehensive tests"""
    print("\n" + "="*60)
    print("COMPREHENSIVE APPLICATION TEST SUITE")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print(f"Timestamp: {results['timestamp']}")
    
    # Run all tests
    test_health_check()
    test_status_endpoint()
    test_file_operations()
    test_rag_indexing()
    test_chat_functionality()
    test_performance_endpoint()
    test_git_integration()
    test_rules_engine()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Passed: {results['tests_passed']}")
    print(f"Failed: {results['tests_failed']}")
    print(f"Total: {results['tests_passed'] + results['tests_failed']}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error['test']}: {error['error']}")
    
    # Save results
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: test_results.json")
    
    return results['tests_failed'] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
