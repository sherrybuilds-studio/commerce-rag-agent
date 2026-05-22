#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the database functions
from shared.database import supabase, save_lead, get_leads

# Test the connection
print("🔍 Testing Supabase connection...\n")

try:
    # Check if credentials are loaded
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env")
        print(f"   SUPABASE_URL: {url}")
        print(f"   SUPABASE_KEY: {key}")
        sys.exit(1)
    
    print(f"✅ Credentials loaded:")
    print(f"   SUPABASE_URL: {url[:20]}...")
    print(f"   SUPABASE_KEY: {key[:20]}...\n")
    
    # Test getting leads (this will verify connection)
    print("📊 Fetching all leads...")
    leads = get_leads()
    
    print(f"✅ Connection successful!")
    print(f"   Total leads in database: {len(leads)}")
    
    if leads:
        print(f"\n   Sample lead: {leads[0]}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Connection failed:")
    print(f"   Error: {str(e)}")
    sys.exit(1)
