#!/usr/bin/env python3
"""
Test script to verify matching scores are calculated and displayed correctly
"""

import sys
sys.path.append('.')

from matching import compute_score
from preprocessing import extract_skills

def test_matching_scores():
    print("=== Testing Matching Scores Calculation ===")

    # Simulate CV skills (from your example)
    cv_skills = ['machine learning', 'typescript', 'aws', 'nlp', 'java', 'go', 'git', 'docker', 'linux', 'sql', 'python']
    print(f"CV Skills: {cv_skills}")

    # Test job data from jobs.json
    test_jobs = [
        {
            "title": "Healthcare Data Analyst",
            "company_name": "MediTech Solutions",
            "skills": ["python", "sql", "machine learning", "statistics"],
            "location": "UK",
            "type": "full-time"
        },
        {
            "title": "NLP Research Engineer",
            "company_name": "EduNext",
            "skills": ["python", "nlp", "tensorflow", "deep learning"],
            "location": "Remote",
            "type": "full-time"
        },
        {
            "title": "Cybersecurity Specialist",
            "company_name": "FinPay",
            "skills": ["network security", "python", "aws", "penetration testing"],
            "location": "Remote",
            "type": "full-time"
        }
    ]

    print("\n=== Calculating Matching Scores ===")

    scored_jobs = []
    for job in test_jobs:
        score, matched_skills = compute_score({"skills": cv_skills}, job["skills"])
        job_copy = job.copy()
        job_copy["match_score"] = score
        job_copy["matched_skills"] = matched_skills
        scored_jobs.append(job_copy)

        print(f"\nJob: {job['title']} - {job['company_name']}")
        print(f"  Job Skills: {job['skills']}")
        print(f"  Matching Score: {score:.1f}%")
        print(f"  Matched Skills: {matched_skills}")

    # Sort by score descending and take top 3
    scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)
    top_3_jobs = scored_jobs[:3]

    print("\n=== Top 3 Jobs (as they should appear) ===")
    for i, job in enumerate(top_3_jobs, 1):
        print(f"\n{i}. {job['title']} - {job['company_name']}")
        print(f"   📍 {job['location']} • 💼 {job['type']}")
        print(f"   🎯 Matching Score: {job['match_score']:.1f}%")
        print(f"   ✅ Matched Skills: {', '.join(job['matched_skills'][:3])}")

    print("\n=== Test Complete ===")
    print("✅ Scores should now be displayed in the job listings!")

if __name__ == "__main__":
    test_matching_scores()