#!/usr/bin/env python3
"""
Test script to debug the job matching issue
"""

import sys
import os
sys.path.append('.')

from parsing import parse_cv
from preprocessing import preprocess_cv
from matching import compute_score
import json

def test_matching():
    print("=== Testing Job Matching ===")

    # 1. Load CV
    try:
        cv_text = parse_cv("cv_test.png")
        cv_data = preprocess_cv(cv_text)
        print(f"✅ CV loaded with skills: {cv_data.get('skills', [])}")
    except Exception as e:
        print(f"❌ Error loading CV: {e}")
        return

    # 2. Load jobs from JSON file
    try:
        with open("jobs.json", "r", encoding="utf-8") as f:
            companies_data = json.load(f)

        # Flatten jobs like in the matching function
        jobs = []
        for company in companies_data:
            for job in company.get("jobs", []):
                job_copy = job.copy()
                job_copy["company_name"] = company["company"]
                jobs.append(job_copy)

        print(f"✅ Loaded {len(jobs)} jobs from JSON")
    except Exception as e:
        print(f"❌ Error loading jobs: {e}")
        return

    # 3. Test matching for each job
    print("\n=== Matching Results ===")
    matches_found = 0

    for i, job in enumerate(jobs):
        job_skills = job.get('skills', [])
        print(f"\nJob {i+1}: {job.get('title')} - Skills: {job_skills}")

        if job_skills:
            score, matched_skills = compute_score(cv_data, job_skills)
            print(f"  Score: {score}%, Matched: {matched_skills}")

            if score > 0:
                matches_found += 1
        else:
            print("  No skills defined for this job")

    print(f"\n=== Summary ===")
    print(f"Total jobs: {len(jobs)}")
    print(f"Jobs with matches: {matches_found}")
    print(f"CV skills: {cv_data.get('skills', [])}")

if __name__ == "__main__":
    test_matching()