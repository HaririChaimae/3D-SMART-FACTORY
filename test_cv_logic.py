#!/usr/bin/env python3
"""
Test script to verify CV processing logic
"""

def test_cv_logic():
    print("=== Testing CV Logic ===")

    # Simulate different cv_data scenarios
    test_cases = [
        {"name": "Valid CV with skills", "data": {"skills": ["python", "sql", "aws"]}},
        {"name": "CV with empty skills", "data": {"skills": []}},
        {"name": "CV with None skills", "data": {"skills": None}},
        {"name": "CV without skills key", "data": {"name": "John"}},
        {"name": "None cv_data", "data": None},
    ]

    for test_case in test_cases:
        cv_data = test_case["data"]
        print(f"\nTest: {test_case['name']}")
        print(f"cv_data: {cv_data}")

        # Test the logic from app.py
        if cv_data and cv_data.get("skills") and len(cv_data.get("skills", [])) > 0:
            skills = cv_data.get("skills", [])
            print(f"✅ Would process CV with skills: {skills}")
            print("✅ Would call process_job_matching()")
        else:
            print("⚠️ Would show warning: CV analysé mais aucune compétence détectée")

    print("\n=== CV Logic Test Complete ===")

if __name__ == "__main__":
    test_cv_logic()