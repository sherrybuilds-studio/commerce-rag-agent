import os

from supabase import create_client

# Get Supabase credentials from environment variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Initialize Supabase client with credentials
supabase = create_client(supabase_url, supabase_key)


def save_lead(lead_data):
    """
    Save a lead to the 'leads' table in Supabase.
    
    Args:
        lead_data: Dictionary containing lead information
                  (e.g., {"name": "John", "email": "john@example.com", "phone": "+1234567890"})
    
    Returns:
        Response object containing the saved lead data
    """
    # Insert the lead_data into the 'leads' table
    response = supabase.table("leads").insert(lead_data).execute()
    
    # Return the response which includes the saved lead with ID
    return response


def get_leads():
    """
    Retrieve all leads from the 'leads' table in Supabase.
    
    Returns:
        List of all lead records from the database
    """
    # Query the 'leads' table and select all columns
    response = supabase.table("leads").select("*").execute()
    
    # Extract and return the data from the response object
    return response.data
