#!/usr/bin/env python3
"""
Test script to verify the app logic for job matching
"""

import sys
sys.path.append('.')

from preprocessing import preprocess_cv
from matching import compute_score

def test_app_logic():
    print("=== Testing App Logic ===")

    # Simulate CV data
    cv_text = "Python developer with experience in machine learning, SQL, AWS, and JavaScript"
    cv_data = preprocess_cv(cv_text)
    print(f"CV skills: {cv_data.get('skills', [])}")

    # Simulate jobs data (like from database)
    jobs = [
        {
            'id': 1,
            'title': 'Backend Developer',
            'company_name': 'Pied Piper',
            'skills': ['python', 'javascript', 'redis'],
            'location': 'US',
            'type': 'full-time'
        },
        {
            'id': 2,
            'title': 'Healthcare Data Analyst',
            'company_name': 'MediTech Solutions',
            'skills': ['python', 'sql', 'machine learning', 'statistics'],
            'location': 'UK',
            'type': 'full-time'
        },
        {
            'id': 3,
            'title': 'Cybersecurity Specialist',
            'company_name': 'FinPay',
            'skills': ['network security', 'python', 'aws', 'penetration testing'],
            'location': 'Remote',
            'type': 'full-time'
        }
    ]

    # Test the matching logic (simulate process_job_matching)
    cv_data["skills"] = [s.lower() for s in cv_data.get("skills", [])]
    for job in jobs:
        if "skills" in job and isinstance(job["skills"], list):
            job["skills"] = [s.lower() for s in job["skills"]]

    scored_jobs = []
    for job in jobs:
        score, matched_skills = compute_score(cv_data, job.get("skills", []))
        if score > 0:
            job_copy = job.copy()
            job_copy["match_score"] = score
            job_copy["matched_skills"] = matched_skills
            scored_jobs.append(job_copy)

    scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)
    matched_jobs = scored_jobs[:3]

    print(f"\nMatched jobs: {len(matched_jobs)}")
    for job in matched_jobs:
        print(f"- {job['title']}: {job['match_score']}% ({job['matched_skills']})")

    # Test the filtering logic
    if matched_jobs:
        base_jobs = matched_jobs
        print(f"\nUsing matched jobs as base: {len(base_jobs)} jobs")
    else:
        base_jobs = jobs
        print(f"\nUsing all jobs as base: {len(base_jobs)} jobs")

    # Simulate search/location/type filters
    search_term = ""
    location_filter = "All"
    type_filter = "All"

    filtered_jobs = base_jobs
    if search_term:
        filtered_jobs = [job for job in filtered_jobs if
            search_term.lower() in job['title'].lower() or
            search_term.lower() in job['company_name'].lower() or
            (job['skills'] and any(search_term.lower() in skill.lower() for skill in job['skills']))]

    if location_filter != "All":
        filtered_jobs = [job for job in filtered_jobs if job['location'] == location_filter]

    if type_filter != "All":
        filtered_jobs = [job for job in filtered_jobs if job['type'] == type_filter]

    print(f"Filtered jobs: {len(filtered_jobs)}")
    for job in filtered_jobs:
        print(f"- {job['title']} ({job.get('match_score', 0)}%)")

if __name__ == "__main__":
    test_app_logic()