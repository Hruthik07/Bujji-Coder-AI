"""
Deployment Testing Script
Tests all production deployment features
"""
import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8010"
FRONTEND_URL = "http://localhost:80"

def test_health_check() -> bool:
    """Test health check endpoint"""
    print("\n[TEST] Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Health check passed: {data.get('status')}")
            return True
        else:
            print(f"  ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Health check error: {e}")
        return False

def test_status_endpoint() -> bool:
    """Test status endpoint"""
    print("\n[TEST] Status Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Status endpoint working")
            print(f"     - Assistant ready: {data.get('assistant_ready')}")
            print(f"     - RAG enabled: {data.get('rag_enabled')}")
            return True
        else:
            print(f"  ❌ Status endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Status endpoint error: {e}")
        return False

def test_authentication() -> Dict[str, Any]:
    """Test authentication endpoints"""
    print("\n[TEST] Authentication...")
    results = {"register": False, "login": False, "me": False}
    
    # Test registration
    try:
        register_data = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "TestPassword123!"
        }
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json=register_data,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            print(f"  ✅ Registration successful")
            results["register"] = True
            results["tokens"] = {"access": access_token, "refresh": refresh_token}
            results["username"] = register_data["username"]
            results["password"] = register_data["password"]
        else:
            print(f"  ❌ Registration failed: {response.status_code}")
            print(f"     Response: {response.text}")
            return results
    except Exception as e:
        print(f"  ❌ Registration error: {e}")
        return results
    
    # Test login
    try:
        login_data = {
            "username": results["username"],
            "password": results["password"]
        }
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            print(f"  ✅ Login successful")
            results["login"] = True
            results["tokens"]["access"] = access_token
        else:
            print(f"  ❌ Login failed: {response.status_code}")
            return results
    except Exception as e:
        print(f"  ❌ Login error: {e}")
        return results
    
    # Test /api/auth/me
    try:
        headers = {"Authorization": f"Bearer {results['tokens']['access']}"}
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Get current user successful")
            print(f"     - Username: {data.get('username')}")
            print(f"     - Role: {data.get('role')}")
            results["me"] = True
        else:
            print(f"  ❌ Get current user failed: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Get current user error: {e}")
    
    return results

def test_rate_limiting() -> bool:
    """Test rate limiting"""
    print("\n[TEST] Rate Limiting...")
    try:
        # Make multiple rapid requests
        responses = []
        for i in range(5):
            response = requests.get(f"{BASE_URL}/api/status", timeout=5)
            responses.append(response)
            if "X-RateLimit-Remaining-Minute" in response.headers:
                remaining = response.headers["X-RateLimit-Remaining-Minute"]
                print(f"  Request {i+1}: Remaining: {remaining}")
        
        # Check if rate limit headers are present
        if "X-RateLimit-Remaining-Minute" in responses[0].headers:
            print(f"  ✅ Rate limiting headers present")
            return True
        else:
            print(f"  ⚠️  Rate limiting headers not found")
            return False
    except Exception as e:
        print(f"  ❌ Rate limiting test error: {e}")
        return False

def test_cors() -> bool:
    """Test CORS configuration"""
    print("\n[TEST] CORS Configuration...")
    try:
        response = requests.options(
            f"{BASE_URL}/api/status",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "GET"
            },
            timeout=5
        )
        if "Access-Control-Allow-Origin" in response.headers:
            print(f"  ✅ CORS headers present")
            print(f"     - Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
            return True
        else:
            print(f"  ⚠️  CORS headers not found")
            return False
    except Exception as e:
        print(f"  ❌ CORS test error: {e}")
        return False

def test_frontend() -> bool:
    """Test frontend accessibility"""
    print("\n[TEST] Frontend...")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print(f"  ✅ Frontend accessible")
            return True
        else:
            print(f"  ⚠️  Frontend returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ⚠️  Frontend not accessible: {e}")
        print(f"     (This is OK if frontend is not running)")
        return False

def main():
    """Run all deployment tests"""
    print("=" * 50)
    print("Bujji-Coder-AI Deployment Testing")
    print("=" * 50)
    
    results = {
        "health_check": False,
        "status": False,
        "authentication": False,
        "rate_limiting": False,
        "cors": False,
        "frontend": False
    }
    
    # Test health check
    results["health_check"] = test_health_check()
    if not results["health_check"]:
        print("\n❌ Health check failed. Is the backend running?")
        print("   Start with: docker-compose up -d")
        return False
    
    # Test status endpoint
    results["status"] = test_status_endpoint()
    
    # Test authentication
    auth_results = test_authentication()
    results["authentication"] = auth_results.get("login", False) and auth_results.get("me", False)
    
    # Test rate limiting
    results["rate_limiting"] = test_rate_limiting()
    
    # Test CORS
    results["cors"] = test_cors()
    
    # Test frontend (optional)
    results["frontend"] = test_frontend()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():.<30} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Deployment is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
