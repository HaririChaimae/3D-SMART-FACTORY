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
    Parcourt toutes les entreprises et leurs jobs (format imbriqué ou plat),
    calcule le score de matching et renvoie la liste des jobs correspondants.
    """
    matches = []

    for item in jobs_data:
        # Cas 1 : format imbriqué (company → jobs)
        if "jobs" in item:
            company_name = item.get("company", "Sans nom")
            for job in item.get("jobs", []):
                score, matched_skills = compute_score(cv_data, job.get("skills", []))
                if score > 0:
                    job_copy = job.copy()
                    job_copy["company_name"] = company_name
                    job_copy["match_score"] = score
                    job_copy["matched_skills"] = matched_skills
                    matches.append(job_copy)

        # Cas 2 : format plat (déjà un job dict)
        else:
            score, matched_skills = compute_score(cv_data, item.get("skills", []))
            if score > 0:
                job_copy = item.copy()
                job_copy["company_name"] = item.get("company_name", item.get("company", "Sans nom"))
                job_copy["match_score"] = score
                job_copy["matched_skills"] = matched_skills
                matches.append(job_copy)

    # Trier par score décroissant
    matches.sort(key=lambda j: j["match_score"], reverse=True)

    return matches
