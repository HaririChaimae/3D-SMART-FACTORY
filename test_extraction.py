# Test script for CV data extraction using the same technique as Adding Admin

from parsing import parse_cv
from preprocessing import preprocess_cv

def test_cv_extraction():
    """Test CV data extraction on available files"""

    test_files = [
        "mycv/resume.txt",
        "data/Untitled document-1.pdf",
        "images/images.png"
    ]

    for file_path in test_files:
        try:
            print(f"\n--- Testing: {file_path} ---")

            # Extract text
            cv_text = parse_cv(file_path)
            print(f"Text extracted: {len(cv_text)} characters")

            # Extract data
            cv_data = preprocess_cv(cv_text)

            print(f"Name: {cv_data['name']}")
            print(f"Email: {cv_data['email']}")
            print(f"Phone: {cv_data['phone']}")
            print(f"Skills: {cv_data['skills']}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    test_cv_extraction()