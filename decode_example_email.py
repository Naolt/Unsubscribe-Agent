#!/usr/bin/env python3
"""
Script to decode the quoted-printable encoded example email
"""

import quopri
from example_email import example_email

def decode_example_email():
    """Decode the quoted-printable encoded example email"""
    
    print("Original encoded content (first 200 chars):")
    print("-" * 60)
    print(example_email[:200])
    print("...")
    
    print("\nDecoded content (first 200 chars):")
    print("-" * 60)
    
    try:
        decoded = quopri.decodestring(example_email.encode('utf-8')).decode('utf-8')
        print(decoded[:200])
        print("...")
        
        print(f"\nSize comparison:")
        print(f"Original: {len(example_email)} characters")
        print(f"Decoded:  {len(decoded)} characters")
        
        # Look for unsubscribe links in the decoded content
        if "unsubscribe" in decoded.lower():
            print(f"\n✅ Found 'unsubscribe' in decoded content")
        else:
            print(f"\n❌ No 'unsubscribe' found in decoded content")
            
        # Look for href attributes
        href_count = decoded.count('href=')
        print(f"Found {href_count} href attributes in decoded content")
        
    except Exception as e:
        print(f"Error decoding: {e}")

if __name__ == "__main__":
    decode_example_email()
