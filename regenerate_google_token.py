#!/usr/bin/env python3
"""
Script to regenerate Google OAuth token locally
Run this script to generate a new token.json file, then encode it to base64 for DigitalOcean
"""

import os
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]

def regenerate_token():
    """Regenerate Google OAuth token"""
    creds_file = "credentials.json"
    token_file = "token.json"
    
    if not os.path.exists(creds_file):
        print(f"❌ Error: {creds_file} not found!")
        print("   Make sure credentials.json is in the current directory")
        return
    
    print("🔄 Starting OAuth flow...")
    print("   A browser window will open - please authorize the application")
    
    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Save token
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
    
    print(f"✅ Token saved to {token_file}")
    
    # Encode to base64
    with open(token_file, 'rb') as f:
        token_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    print("\n📋 Base64 encoded token (copy this to GOOGLE_TOKEN_BASE64 in DigitalOcean):")
    print("-" * 80)
    print(token_base64)
    print("-" * 80)
    
    # Also save to file for convenience
    output_file = "token_base64.txt"
    with open(output_file, 'w') as f:
        f.write(token_base64)
    print(f"\n💾 Also saved to {output_file} (DO NOT COMMIT THIS FILE)")

if __name__ == "__main__":
    regenerate_token()

