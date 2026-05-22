# Quick debug test
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if api_key:
    print(f"✓ API Key loaded: {api_key[:20]}...")
else:
    print("✗ API Key NOT found")
    exit(1)

# Test import
try:
    from anthropic import Anthropic
    print("✓ Anthropic SDK imported successfully")
except Exception as e:
    print(f"✗ Failed to import Anthropic: {e}")
    exit(1)

# Test client creation
try:
    client = Anthropic(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    print("✓ Client created successfully")
except Exception as e:
    print(f"✗ Failed to create client: {e}")
    exit(1)

print("\nAll checks passed! Ready to call API.")
print("Attempting API call to OpenRouter...")

try:
    response = client.messages.create(
        model="anthropic/claude-3.5-haiku:beta",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": "Explain RAG in 2 sentences"
            }
        ]
    )
    print("\n✓ API call successful!")
    print("Claude's Response:")
    print(response.content[0].text)
except Exception as e:
    print(f"\n✗ API call failed: {type(e).__name__}")
    print(f"Error: {str(e)[:200]}")
