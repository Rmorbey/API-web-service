#!/usr/bin/env python3
"""
Test script for the fundraising scraper
"""

import httpx
from bs4 import BeautifulSoup
import re
import json

def test_scraper():
    url = 'https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015'
    
    print("Testing JustGiving scraper...")
    
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        script_tags = soup.find_all('script')
        
        print(f"Found {len(script_tags)} script tags")
        
        for i, script in enumerate(script_tags):
            if script.string and 'Gabriella Cook' in script.string:
                print(f"Found donation data in script {i}")
                script_content = script.string
                
                # Test different patterns
                if 'totalAmount' in script_content:
                    print("Found totalAmount in script")
                    # Look for the value 1500 (which is £15.00 in pence)
                    if '1500' in script_content:
                        print("Found £15.00 total amount")
                
                if 'donationCount' in script_content:
                    print("Found donationCount in script")
                    if '2' in script_content:
                        print("Found 2 donations")
                
                # Test regex patterns
                total_match = re.search(r'"totalAmount":\{"value":(\d+)', script_content)
                if total_match:
                    total_raised = float(total_match.group(1)) / 100
                    print(f"Regex found total: £{total_raised:.2f}")
                
                count_match = re.search(r'"donationCount":(\d+)', script_content)
                if count_match:
                    count = int(count_match.group(1))
                    print(f"Regex found count: {count}")
                
                # Look for donation names
                if 'Gabriella Cook' in script_content:
                    print("Found Gabriella Cook")
                if 'Russell Morbey' in script_content:
                    print("Found Russell Morbey")
                
                break
        else:
            print("No script with donation data found")

if __name__ == "__main__":
    test_scraper()
