# Import the os module to read environment variables (like API keys) safely
import os

# Import dotenv to load environment variables from .env file
from dotenv import load_dotenv

# Import the Anthropic SDK that we just installed - this lets us talk to Claude
from anthropic import Anthropic

# Load environment variables from the .env file in the current directory
# This reads the .env file and adds its variables to os.environ
load_dotenv()

# Use os.getenv() to read the OPENROUTER_API_KEY from the system environment
# This is safe - never hardcode API keys in code
# If the key is not found, it returns None (we don't set a default to catch missing keys early)
api_key = os.getenv("OPENROUTER_API_KEY")

# Create an Anthropic client that connects to OpenRouter instead of Anthropic's servers
# base_url tells the client to send requests to OpenRouter, not anthropic.com
# api_key is our authentication token for OpenRouter
client = Anthropic(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

# Send a request to Claude 3.5 Haiku through OpenRouter
# We create a message with our prompt and ask for a response
response = client.messages.create(
    # model: which AI model to use - OpenRouter uses provider/model format
    model="anthropic/claude-3.5-haiku",
    # max_tokens: the maximum number of words we allow Claude to respond with
    max_tokens=100,
    # messages: a list of messages in the conversation - we're sending one user message
    messages=[
        {
            # role: "user" means this is a message from the person asking the question
            "role": "user",
            # content: the actual question or instruction we're sending to Claude
            "content": "Explain RAG in 2 sentences"
        }
    ]
)

# Extract the text from Claude's response
# response.content[0] is the first response block, .text gets the actual text
answer = response.content[0].text

# Print the response so we can see what Claude said
print("Claude's Response:")
print(answer)

# Also write to file for verification
with open('output.txt', 'w') as f:
    f.write("Claude's Response:\n")
    f.write(answer)
