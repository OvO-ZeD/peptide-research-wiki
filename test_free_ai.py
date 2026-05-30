#!/usr/bin/env python3
"""
Test script for FREE Hugging Face AI integration
Tests the API endpoint without needing to run the full Flask app
"""

import requests
import json

def test_hugging_face_api():
    """Test that Hugging Face API works without authentication"""

    print("🧪 Testing FREE Hugging Face API (no API key required!)\n")

    # Free model - no authentication needed
    model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    api_url = f"https://api-inference.huggingface.co/models/{model}"

    # Simple test prompt
    prompt = """You are an expert research assistant specializing in peptides.

USER: What is BPC-157 and what are its benefits?

ASSISTANT:"""

    print(f"📡 Calling: {api_url}")
    print(f"🤖 Model: {model}")
    print(f"🔓 Authentication: NONE (completely free!)")
    print("\nSending test query: 'What is BPC-157 and what are its benefits?'\n")

    try:
        response = requests.post(
            api_url,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "return_full_text": False
                }
            },
            timeout=30
        )

        print(f"📊 Status Code: {response.status_code}\n")

        if response.status_code == 200:
            result = response.json()

            # Handle response format
            if isinstance(result, list) and len(result) > 0:
                ai_response = result[0].get("generated_text", "")
            elif isinstance(result, dict):
                ai_response = result.get("generated_text", "")
            else:
                ai_response = "Unexpected response format"

            # Clean up response
            if "ASSISTANT:" in ai_response:
                ai_response = ai_response.split("ASSISTANT:")[-1].strip()

            print("✅ SUCCESS! AI Response:")
            print("-" * 80)
            print(ai_response)
            print("-" * 80)
            print("\n🎉 The FREE AI service is working perfectly!")
            print("💰 Cost: $0.00 (no API key needed)")

        elif response.status_code == 503:
            print("⏳ Model is loading (first-time startup)")
            print("💡 This is normal! Wait 20 seconds and try again.")
            print("🚀 After loading once, it will be fast!")

        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")

    except requests.Timeout:
        print("⏱️  Request timed out. This can happen if the model is loading.")
        print("💡 Try again in 20 seconds!")

    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        print("💡 Check your internet connection")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_alternative_model():
    """Test a faster alternative model"""

    print("\n" + "="*80)
    print("🧪 Testing alternative fast model (Llama 3.2 3B)\n")

    model = "meta-llama/Llama-3.2-3B-Instruct"
    api_url = f"https://api-inference.huggingface.co/models/{model}"

    prompt = """You are a helpful AI assistant.

USER: Hello! Can you help me with peptides?

ASSISTANT:"""

    print(f"📡 Calling: {api_url}")
    print(f"🤖 Model: {model} (smaller, faster)")
    print(f"🔓 Authentication: NONE (completely free!)")
    print("\nSending test query...\n")

    try:
        response = requests.post(
            api_url,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 256,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            },
            timeout=20
        )

        print(f"📊 Status Code: {response.status_code}\n")

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                ai_response = result[0].get("generated_text", "")
            else:
                ai_response = str(result)

            print("✅ Alternative model working!")
            print(f"Response preview: {ai_response[:200]}...")

        elif response.status_code == 503:
            print("⏳ Model loading...")

        else:
            print(f"Status: {response.status_code}")

    except Exception as e:
        print(f"Note: {e}")


if __name__ == "__main__":
    print("="*80)
    print("🚀 FREE AI SERVICE TEST")
    print("="*80)
    print("\n✅ No API keys required")
    print("✅ No authentication needed")
    print("✅ Completely free to use")
    print("✅ No credit card required\n")
    print("="*80 + "\n")

    # Test main model
    test_hugging_face_api()

    # Test alternative (optional)
    # Uncomment to test faster alternative model:
    # test_alternative_model()

    print("\n" + "="*80)
    print("📝 NEXT STEPS:")
    print("="*80)
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run the app: python app.py")
    print("3. Navigate to Ask AI page")
    print("4. Start chatting - NO API KEYS NEEDED!")
    print("\n💡 First request may take 20 seconds (model loading)")
    print("   Subsequent requests will be fast!\n")
