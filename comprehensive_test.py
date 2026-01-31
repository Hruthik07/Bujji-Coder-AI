"""
Comprehensive Application Testing Suite
Tests all features and measures performance
"""
import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8001"
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
    print("0. HEALTH CHECK TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=2)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Health check endpoint", True, duration)
            
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Assistant Ready: {data.get('assistant_ready', False)}")
            print(f"   RAG Status: {data.get('rag_status', 'N/A')}")
            
            services = data.get('services', {})
            print(f"   Services: Git={services.get('git', False)}, Rules={services.get('rules', False)}, Performance={services.get('performance', False)}")
            
            results["performance"]["health_check"] = duration
            return True, data
        else:
            log_test("Health check endpoint", False, duration, f"Status {response.status_code}")
            return False, None
    except Exception as e:
        duration = time.time() - start
        log_test("Health check endpoint", False, duration, e)
        return False, None

def test_backend_status():
    """Test backend status endpoint"""
    print("\n" + "="*60)
    print("1. BACKEND STATUS TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Status endpoint", True, duration)
            
            print(f"   Assistant Ready: {data.get('assistant_ready', False)}")
            print(f"   RAG Enabled: {data.get('rag_enabled', False)}")
            print(f"   RAG Indexed: {data.get('rag_indexed', False)}")
            print(f"   Model: {data.get('model', 'N/A')}")
            print(f"   Hybrid Mode: {data.get('hybrid_mode', False)}")
            
            providers = data.get('available_providers', {})
            print(f"   Providers: {', '.join([p for p, v in providers.items() if v])}")
            
            results["performance"]["status_endpoint"] = duration
            return True, data
        else:
            log_test("Status endpoint", False, duration, f"Status {response.status_code}")
            return False, None
    except Exception as e:
        duration = time.time() - start
        log_test("Status endpoint", False, duration, e)
        return False, None

def test_file_operations():
    """Test file listing and operations"""
    print("\n" + "="*60)
    print("2. FILE OPERATIONS TEST")
    print("="*60)
    
    # Test file listing
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/files?directory=.", timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            log_test("File listing", True, duration)
            print(f"   Found {len(items)} items")
            results["performance"]["file_listing"] = duration
        else:
            log_test("File listing", False, duration, f"Status {response.status_code}")
    except Exception as e:
        duration = time.time() - start
        log_test("File listing", False, duration, e)

def test_chat_endpoint():
    """Test chat endpoint"""
    print("\n" + "="*60)
    print("3. CHAT ENDPOINT TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "Hello, what can you do?"},
            timeout=30
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                log_test("Chat endpoint", True, duration)
                print(f"   Response length: {len(data.get('response', ''))} chars")
                results["performance"]["chat_endpoint"] = duration
            else:
                log_test("Chat endpoint", False, duration, data.get('error', 'Unknown error'))
        else:
            log_test("Chat endpoint", False, duration, f"Status {response.status_code}")
    except Exception as e:
        duration = time.time() - start
        log_test("Chat endpoint", False, duration, e)

def test_validation_service():
    """Test validation endpoint"""
    print("\n" + "="*60)
    print("4. VALIDATION SERVICE TEST")
    print("="*60)
    
    test_diff = """--- a/test.py
+++ b/test.py
@@ -1,1 +1,1 @@
-print('hello')
+print('hello world')
"""
    
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/api/diff/validate",
            json={
                "diff_text": test_diff,
                "file_path": "test.py"
            },
            timeout=15
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Validation endpoint", True, duration)
            print(f"   Valid: {data.get('is_valid', False)}")
            results["performance"]["validation_endpoint"] = duration
        else:
            log_test("Validation endpoint", False, duration, f"Status {response.status_code}")
    except Exception as e:
        duration = time.time() - start
        log_test("Validation endpoint", False, duration, e)

def test_stats_endpoint():
    """Test stats endpoint"""
    print("\n" + "="*60)
    print("5. STATS ENDPOINT TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Stats endpoint", True, duration)
            
            if 'cost' in data:
                cost = data['cost']
                print(f"   Total Requests: {cost.get('total_requests', 0)}")
                print(f"   Estimated Cost: ${cost.get('estimated_cost', 0):.4f}")
            
            if 'rag' in data:
                rag = data['rag']
                print(f"   RAG Chunks: {rag.get('total_chunks', 0)}")
            
            results["performance"]["stats_endpoint"] = duration
        else:
            log_test("Stats endpoint", False, duration, f"Status {response.status_code}")
    except Exception as e:
        duration = time.time() - start
        log_test("Stats endpoint", False, duration, e)

def test_performance_endpoint():
    """Test performance monitoring endpoint"""
    print("\n" + "="*60)
    print("6. PERFORMANCE MONITORING TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/performance", timeout=6)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Performance endpoint", True, duration)
            
            if 'current' in data:
                current = data['current']
                print(f"   Memory: {current.get('memory', {}).get('current_mb', 0):.1f} MB")
                if 'response_times' in current and current['response_times']:
                    print(f"   Avg Response Time: {current['response_times'].get('avg_ms', 0):.1f}ms")
            
            results["performance"]["performance_endpoint"] = duration
        elif response.status_code == 504:
            duration = time.time() - start
            log_test("Performance endpoint", False, duration, "Timeout (504)")
        else:
            log_test("Performance endpoint", False, duration, f"Status {response.status_code}")
    except requests.exceptions.Timeout:
        duration = time.time() - start
        log_test("Performance endpoint", False, duration, "Request timeout")
    except Exception as e:
        duration = time.time() - start
        log_test("Performance endpoint", False, duration, e)

def test_git_endpoints():
    """Test Git integration endpoints"""
    print("\n" + "="*60)
    print("7. GIT INTEGRATION TEST")
    print("="*60)
    
    # Test git status
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/git/status", timeout=6)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Git status endpoint", True, duration)
            print(f"   Is Repo: {data.get('is_repo', False)}")
            if data.get('is_repo'):
                print(f"   Current Branch: {data.get('branch', 'N/A')}")
                print(f"   Has Changes: {data.get('has_changes', False)}")
            results["performance"]["git_status"] = duration
        elif response.status_code == 504:
            duration = time.time() - start
            log_test("Git status endpoint", False, duration, "Timeout (504)")
        else:
            log_test("Git status endpoint", False, duration, f"Status {response.status_code}")
    except requests.exceptions.Timeout:
        duration = time.time() - start
        log_test("Git status endpoint", False, duration, "Request timeout")
    except Exception as e:
        duration = time.time() - start
        log_test("Git status endpoint", False, duration, e)

def test_rules_endpoint():
    """Test rules engine endpoint"""
    print("\n" + "="*60)
    print("8. RULES ENGINE TEST")
    print("="*60)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/rules", timeout=4)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("Rules endpoint", True, duration)
            print(f"   Rules Exist: {data.get('exists', False)}")
            if data.get('exists'):
                print(f"   Rules Size: {data.get('info', {}).get('size', 0)} chars")
            results["performance"]["rules_endpoint"] = duration
        elif response.status_code == 504:
            duration = time.time() - start
            log_test("Rules endpoint", False, duration, "Timeout (504)")
        else:
            log_test("Rules endpoint", False, duration, f"Status {response.status_code}")
    except requests.exceptions.Timeout:
        duration = time.time() - start
        log_test("Rules endpoint", False, duration, "Request timeout")
    except Exception as e:
        duration = time.time() - start
        log_test("Rules endpoint", False, duration, e)

def test_rag_indexing():
    """Test RAG indexing"""
    print("\n" + "="*60)
    print("9. RAG INDEXING TEST")
    print("="*60)
    
    # Check if already indexed
    try:
        status_response = requests.get(f"{BASE_URL}/api/status", timeout=10)
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data.get('rag_indexed'):
                log_test("RAG indexing", True, 0)
                print("   Already indexed")
                return
    except Exception:
        pass
    
    # Try to trigger indexing (non-blocking)
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/api/index?force=false", timeout=5)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("RAG indexing trigger", True, duration)
            print(f"   Status: {data.get('status', 'N/A')}")
            results["performance"]["rag_indexing_trigger"] = duration
        else:
            log_test("RAG indexing trigger", False, duration, f"Status {response.status_code}")
    except Exception as e:
        duration = time.time() - start
        log_test("RAG indexing trigger", False, duration, e)

def calculate_performance_summary():
    """Calculate performance summary"""
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    
    if results["performance"]:
        total_time = sum(results["performance"].values())
        avg_time = total_time / len(results["performance"])
        max_time = max(results["performance"].values())
        min_time = min(results["performance"].values())
        
        print(f"Total Test Time: {total_time:.2f}s")
        print(f"Average Response Time: {avg_time:.2f}s")
        print(f"Fastest Endpoint: {min_time:.2f}s")
        print(f"Slowest Endpoint: {max_time:.2f}s")
        
        print("\nEndpoint Performance:")
        for endpoint, duration in sorted(results["performance"].items(), key=lambda x: x[1]):
            print(f"   {endpoint}: {duration:.2f}s")

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = results["tests_passed"] + results["tests_failed"]
    pass_rate = (results["tests_passed"] / total * 100) if total > 0 else 0
    
    print(f"Tests Passed: {results['tests_passed']}")
    print(f"Tests Failed: {results['tests_failed']}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    if results["errors"]:
        print("\nErrors Found:")
        for error in results["errors"]:
            print(f"   - {error['test']}: {error['error']}")
    
    print("\n" + "="*60)
    
    if results["tests_failed"] == 0:
        print("[SUCCESS] All tests passed!")
    else:
        print("[WARNING] Some tests failed. Check errors above.")
    
    print("="*60)

def main():
    print("\n" + "="*60)
    print("COMPREHENSIVE APPLICATION TEST SUITE")
    print("="*60)
    print(f"Testing: {BASE_URL}")
    print(f"Time: {results['timestamp']}")
    
    # Run all tests
    test_health_check()
    test_backend_status()
    test_file_operations()
    test_chat_endpoint()
    test_validation_service()
    test_stats_endpoint()
    test_performance_endpoint()
    test_git_endpoints()
    test_rules_endpoint()
    test_rag_indexing()
    
    # Calculate and display performance
    calculate_performance_summary()
    
    # Print summary
    print_summary()
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n[INFO] Test results saved to test_results.json")

if __name__ == "__main__":
    main()
