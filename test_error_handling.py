#!/usr/bin/env python3
"""
Test script to verify error handling in CV parsing
"""

import sys
sys.path.append('.')

from parsing import parse_cv

def test_error_handling():
    print("=== Testing Error Handling ===")

    # Test with a non-existent file
    try:
        result = parse_cv("non_existent_file.pdf")
        print("❌ Should have failed for non-existent file")
    except Exception as e:
        print(f"✅ Correctly handled non-existent file: {e}")

    # Test with invalid file content
    try:
        # Create a temporary file with invalid content
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"This is not a valid PDF content")
            tmp_path = tmp.name

        try:
            result = parse_cv(tmp_path)
            print("❌ Should have failed for invalid PDF")
        except Exception as e:
            print(f"✅ Correctly handled invalid PDF: {e}")
        finally:
            os.remove(tmp_path)
    except Exception as e:
        print(f"Error in test: {e}")

    print("\n=== Error Handling Test Complete ===")

if __name__ == "__main__":
    test_error_handling()