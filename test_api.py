"""Test script to verify the classification API."""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_health():
    """Test health endpoint."""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_classify():
    """Test classification endpoint."""
    print("🔍 Testing classification endpoint...")
    
    test_title = "Mejoramiento del servicio de agua potable en el distrito de San Juan"
    
    response = requests.post(
        f"{BASE_URL}/api/v1/classify",
        json={"title": test_title}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Request: {test_title}")
    print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")

def test_categories():
    """Test categories endpoint."""
    print("🔍 Testing categories endpoint...")
    response = requests.get(f"{BASE_URL}/api/v1/categories")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total categories: {data.get('total')}")
    print(f"Categories: {list(data.get('categories', {}).keys())}\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Brecha AI Service - API Test")
    print("=" * 60 + "\n")
    
    try:
        test_health()
        test_categories()
        test_classify()
        print("✅ All tests completed!")
    except Exception as e:
        print(f"❌ Error: {e}")
