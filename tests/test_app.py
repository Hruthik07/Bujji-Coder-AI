"""
Quick application test script
Tests backend API endpoints and basic functionality
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def test_backend_status():
    """Test if backend is running and get status"""
    print("=" * 60)
    print("Testing Backend Status")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("[OK] Backend is running!")
            print(f"   Assistant Ready: {data.get('assistant_ready', False)}")
            print(f"   RAG Enabled: {data.get('rag_enabled', False)}")
            print(f"   RAG Indexed: {data.get('rag_indexed', False)}")
            print(f"   Model: {data.get('model', 'N/A')}")
            print(f"   Hybrid Mode: {data.get('hybrid_mode', False)}")
            print(f"   Available Providers:")
            providers = data.get('available_providers', {})
            for provider, available in providers.items():
                status = "[OK]" if available else "[X]"
                print(f"     {status} {provider.capitalize()}")
            return True
        else:
            print(f"[ERROR] Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Backend is not running on port 8001")
        print("   Start it with: cd web/backend && python app.py")
        return False
    except Exception as e:
        print(f"[ERROR] Error checking backend: {e}")
        return False

def test_file_listing():
    """Test file listing endpoint"""
    print("\n" + "=" * 60)
    print("Testing File Listing")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/files?directory=.", timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            print(f"[OK] File listing works! Found {len(items)} items")
            if items:
                print("   Sample files:")
                for item in items[:5]:
                    print(f"     - {item.get('name', 'N/A')}")
            return True
        else:
            print(f"[ERROR] File listing returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing file listing: {e}")
        return False

def test_validation_endpoint():
    """Test validation endpoint"""
    print("\n" + "=" * 60)
    print("Testing Validation Endpoint")
    print("=" * 60)
    
    test_diff = """--- a/test.py
+++ b/test.py
@@ -1,1 +1,1 @@
-print('hello')
+print('hello world')
"""
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/diff/validate",
            json={
                "diff_text": test_diff,
                "file_path": "test.py"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("[OK] Validation endpoint works!")
            print(f"   Valid: {data.get('is_valid', False)}")
            return True
        else:
            print(f"[ERROR] Validation endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing validation: {e}")
        return False

def test_stats_endpoint():
    """Test stats endpoint"""
    print("\n" + "=" * 60)
    print("Testing Stats Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("[OK] Stats endpoint works!")
            if 'cost' in data:
                cost = data['cost']
                print(f"   Total Requests: {cost.get('total_requests', 0)}")
                print(f"   Estimated Cost: ${cost.get('estimated_cost', 0):.4f}")
            return True
        else:
            print(f"[ERROR] Stats endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing stats: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("AI Coding Assistant - Application Test")
    print("=" * 60 + "\n")
    
    # Test backend status
    if not test_backend_status():
        print("\n[ERROR] Backend is not running. Please start it first.")
        print("   Command: cd web/backend && python app.py")
        sys.exit(1)
    
    # Test other endpoints
    test_file_listing()
    test_validation_endpoint()
    test_stats_endpoint()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("[OK] Backend is running and responding")
    print("\nNext Steps:")
    print("1. Open browser: http://localhost:3001")
    print("2. Test web interface features:")
    print("   - Chat with assistant")
    print("   - File tree navigation")
    print("   - Model selection")
    print("   - Terminal panel")
    print("   - Git integration")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
