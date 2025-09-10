import json

def compute_score(cv_data, job_skills):
    """
    Calcule un score de matching entre les skills du CV et les skills du job.
    """
    cv_skills = set([s.lower() for s in cv_data.get("skills", [])])
    job_skills = set([s.lower() for s in job_skills])

    if not job_skills:
        return 0.0, []

    matched = cv_skills.intersection(job_skills)
    score = len(matched) / len(job_skills)

    return round(score * 100, 2), list(matched)


def match_jobs(cv_data, jobs_data):
    """
    Parcourt toutes les entreprises et leurs jobs dans le JSON,
    calcule le score de matching et renvoie le meilleur match
    (job_title @ company).
    """
    best_match = None
    best_score = 0

    for company in jobs_data:
        company_name = company.get("company", "Sans nom")
        for job in company.get("jobs", []):
            job_title = job.get("title", "Sans titre")
            job_skills = job.get("skills", [])

            score, matched_skills = compute_score(cv_data, job_skills)

            if score > best_score:
                best_score = score
                best_match = f"{job_title} @ {company_name}"

    return best_match if best_match else "No suitable job found"
