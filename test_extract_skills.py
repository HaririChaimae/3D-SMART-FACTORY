#!/usr/bin/env python3
"""
Test script to debug skill extraction
"""

import sys
sys.path.append('.')

from preprocessing import extract_skills

def test_extract_skills():
    print("=== Testing Skill Extraction ===")

    # Test with text similar to what the user sees
    test_text = """
    Compétences: machine learning, typescript, aws, nlp, java, go, git, docker, linux, sql, python
    Skills: Python, JavaScript, AWS, Docker, Machine Learning
    Technologies: React, Node.js, PostgreSQL, TensorFlow
    """

    print(f"Test text: {test_text.strip()}")

    skills = extract_skills(test_text)
    print(f"Extracted skills: {skills}")
    print(f"Number of skills: {len(skills)}")

    # Test edge cases
    print("\n=== Edge Cases ===")

    # Empty text
    empty_skills = extract_skills("")
    print(f"Empty text skills: {empty_skills}")

    # Text without skills
    no_skills = extract_skills("This is just some random text without any technical skills mentioned.")
    print(f"No skills text: {no_skills}")

    # Text with only one skill
    one_skill = extract_skills("I know Python programming very well.")
    print(f"One skill text: {one_skill}")

    print("\n=== Skill Extraction Test Complete ===")

if __name__ == "__main__":
    test_extract_skills()