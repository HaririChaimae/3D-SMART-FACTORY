# main.py

from parsing import parse_cv
from preprocessing import preprocess_cv
from matching import compute_score
import json

if __name__ == "__main__":
    # 1. Charger un CV (PDF ou image parsé en texte brut)
    cv_text = parse_cv(r"C:\Users\PC\OneDrive\Documents\Bureau\stage2\data\jobs\cvs\cv_test.png")

    # 2. Transformer en infos structurées
    cv_data = preprocess_cv(cv_text)
    print("=== CV extrait ===")
    print(cv_data)

    # 3. Charger tous les jobs depuis le JSON
    with open("jobs.json", "r", encoding="utf-8") as f:
        companies = json.load(f)

    # 4. Calculer le score pour chaque job
    all_scores = []
    for company in companies:
        for job in company["jobs"]:
            score, matched_skills = compute_score(cv_data, job)
            if score > 0:  # optionnel : afficher seulement si il y a au moins une compétence commune
                all_scores.append({
                    "company": company["company"],
                    "job_title": job["title"],
                    "score": score,
                    "matched_skills": matched_skills
                })

    # 5. Trier par score décroissant
    all_scores.sort(key=lambda x: x["score"], reverse=True)

    # 6. Afficher les résultats
    for job in all_scores:
        print(f"\n=== Job: {job['job_title']} @ {job['company']} ===")
        print(f"Matching score: {job['score']}%")
        print(f"Compétences en commun: {job['matched_skills']}")
