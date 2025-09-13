#!/usr/bin/env python3
"""
Ajout de données de test - Entretien Automatisé
==============================================

Script pour ajouter des données de test réalistes à la base de données.
"""

import os
import sys
from datetime import datetime, timedelta
import random

# Ajouter le répertoire courant au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import (
    add_recruiter, add_company, add_job, add_candidate,
    get_db_connection, DB_TYPE
)

def add_test_data():
    """Ajoute des données de test réalistes"""
    print("🎯 Ajout de données de test - Entretien Automatisé")
    print("=" * 60)

    try:
        # 1. Ajouter des recruteurs de test
        print("👔 Ajout des recruteurs...")
        recruiters = [
            ("Alice Dupont", "alice@techcorp.com", "alice123", None),
            ("Marc Leroy", "marc@innovate.fr", "marc123", None),
            ("Sophie Martin", "sophie@startup.io", "sophie123", None),
        ]

        recruiter_ids = []
        for username, email, password, profile_pic in recruiters:
            try:
                add_recruiter(username, email, password, profile_pic)
                print(f"  ✅ {username} ajouté")
                # Récupérer l'ID du recruteur ajouté
                conn = get_db_connection()
                cur = conn.cursor()
                if DB_TYPE == 'sqlite':
                    cur.execute("SELECT id FROM recruiters WHERE email = ?", (email,))
                else:
                    cur.execute("SELECT id FROM recruiters WHERE email = %s", (email,))
                result = cur.fetchone()
                if result:
                    recruiter_ids.append(result[0])
                cur.close()
                conn.close()
            except Exception as e:
                print(f"  ⚠️ Erreur avec {username}: {e}")

        print(f"✅ {len(recruiter_ids)} recruteurs ajoutés")

        # 2. Ajouter des entreprises de test
        print("\n🏢 Ajout des entreprises...")
        companies = [
            ("TechCorp", "https://techcorp.com", True, "Technology", "50-200"),
            ("Innovate France", "https://innovate.fr", False, "Consulting", "10-50"),
            ("Startup.io", "https://startup.io", True, "SaaS", "5-20"),
            ("DataSys", "https://datasys.com", True, "Data Analytics", "20-100"),
        ]

        company_ids = []
        for name, url, remote, market, size in companies:
            try:
                company_id = add_company(name, url, remote, market, size)
                if company_id:
                    company_ids.append(company_id)
                    print(f"  ✅ {name} ajoutée")
                else:
                    print(f"  ⚠️ {name} existe déjà")
            except Exception as e:
                print(f"  ❌ Erreur avec {name}: {e}")

        print(f"✅ {len(company_ids)} entreprises ajoutées")

        # 3. Ajouter des offres d'emploi
        print("\n💼 Ajout des offres d'emploi...")
        jobs_data = [
            {
                "company_id": company_ids[0],
                "recruiter_id": recruiter_ids[0],
                "position": "Senior Python Developer",
                "title": "Développeur Python Senior",
                "description": "Nous recherchons un développeur Python expérimenté pour rejoindre notre équipe. Vous travaillerez sur des projets innovants utilisant Django, Flask et les technologies cloud.",
                "url": "https://techcorp.com/jobs/python-dev",
                "job_type": "full-time",
                "location": "Paris",
                "skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS"],
                "salary_from": 45000,
                "salary_to": 65000,
                "salary_currency": "EUR",
                "equity_from": 0.5,
                "equity_to": 1.0,
                "perks": ["Remote work", "Health insurance", "Training budget"],
                "apply_url": "https://techcorp.com/apply/python-dev"
            },
            {
                "company_id": company_ids[1],
                "recruiter_id": recruiter_ids[1],
                "position": "Full Stack Developer",
                "title": "Développeur Full Stack",
                "description": "Rejoignez notre équipe pour développer des applications web modernes. Technologies : React, Node.js, MongoDB.",
                "url": "https://innovate.fr/jobs/fullstack",
                "job_type": "full-time",
                "location": "Lyon",
                "skills": ["JavaScript", "React", "Node.js", "MongoDB", "Express"],
                "salary_from": 40000,
                "salary_to": 55000,
                "salary_currency": "EUR",
                "equity_from": 0.0,
                "equity_to": 0.0,
                "perks": ["Flexible hours", "Home office"],
                "apply_url": "https://innovate.fr/apply/fullstack"
            },
            {
                "company_id": company_ids[2],
                "recruiter_id": recruiter_ids[2],
                "position": "Data Scientist",
                "title": "Data Scientist",
                "description": "Vous analyserez des données complexes et développerez des modèles de machine learning pour nos clients.",
                "url": "https://startup.io/jobs/data-scientist",
                "job_type": "full-time",
                "location": "Remote",
                "skills": ["Python", "Machine Learning", "Pandas", "Scikit-learn", "SQL"],
                "salary_from": 50000,
                "salary_to": 70000,
                "salary_currency": "EUR",
                "equity_from": 1.0,
                "equity_to": 2.0,
                "perks": ["Stock options", "Remote work", "Conference budget"],
                "apply_url": "https://startup.io/apply/data-scientist"
            },
            {
                "company_id": company_ids[3],
                "recruiter_id": recruiter_ids[0],
                "position": "DevOps Engineer",
                "title": "Ingénieur DevOps",
                "description": "Vous gérerez notre infrastructure cloud et automatiserez nos processus de déploiement CI/CD.",
                "url": "https://datasys.com/jobs/devops",
                "job_type": "full-time",
                "location": "Toulouse",
                "skills": ["Docker", "Kubernetes", "AWS", "Terraform", "Jenkins"],
                "salary_from": 48000,
                "salary_to": 62000,
                "salary_currency": "EUR",
                "equity_from": 0.3,
                "equity_to": 0.8,
                "perks": ["Remote work", "Learning budget", "Health insurance"],
                "apply_url": "https://datasys.com/apply/devops"
            },
            {
                "company_id": company_ids[0],
                "recruiter_id": recruiter_ids[1],
                "position": "Frontend Developer",
                "title": "Développeur Frontend",
                "description": "Créez des interfaces utilisateur exceptionnelles avec React et TypeScript.",
                "url": "https://techcorp.com/jobs/frontend",
                "job_type": "full-time",
                "location": "Remote",
                "skills": ["JavaScript", "React", "TypeScript", "CSS", "HTML"],
                "salary_from": 38000,
                "salary_to": 52000,
                "salary_currency": "EUR",
                "equity_from": 0.2,
                "equity_to": 0.5,
                "perks": ["Remote work", "Flexible hours"],
                "apply_url": "https://techcorp.com/apply/frontend"
            }
        ]

        jobs_added = 0
        for job_data in jobs_data:
            try:
                # Calculer une date de publication récente
                days_ago = random.randint(0, 30)
                posted_date = datetime.now() - timedelta(days=days_ago)

                add_job(
                    company_id=job_data["company_id"],
                    recruiter_id=job_data["recruiter_id"],
                    position=job_data["position"],
                    title=job_data["title"],
                    description=job_data["description"],
                    url=job_data["url"],
                    job_type=job_data["job_type"],
                    posted=posted_date.date(),
                    location=job_data["location"],
                    skills=job_data["skills"],
                    salary_from=job_data["salary_from"],
                    salary_to=job_data["salary_to"],
                    salary_currency=job_data["salary_currency"],
                    equity_from=job_data["equity_from"],
                    equity_to=job_data["equity_to"],
                    perks=job_data["perks"],
                    apply_url=job_data["apply_url"]
                )
                print(f"  ✅ {job_data['title']} ajouté")
                jobs_added += 1
            except Exception as e:
                print(f"  ❌ Erreur avec {job_data['title']}: {e}")

        print(f"✅ {jobs_added} offres d'emploi ajoutées")

        # 4. Ajouter quelques candidats de test
        print("\n👨‍🎓 Ajout de candidats de test...")
        candidates_data = [
            ("Jean Dupont", "jean.dupont@email.com", "Développeur Python expérimenté", recruiter_ids[0]),
            ("Marie Leroy", "marie.leroy@email.com", "Data Scientist junior", recruiter_ids[1]),
            ("Pierre Martin", "pierre.martin@email.com", "Full Stack Developer", recruiter_ids[2]),
        ]

        candidates_added = 0
        for username, email, job_matching, recruiter_id in candidates_data:
            try:
                success, password = add_candidate(username, email, job_matching, "", recruiter_id)
                if success:
                    print(f"  ✅ {username} ajouté (mot de passe: {password})")
                    candidates_added += 1
                else:
                    print(f"  ⚠️ {username} existe déjà")
            except Exception as e:
                print(f"  ❌ Erreur avec {username}: {e}")

        print(f"✅ {candidates_added} candidats ajoutés")

        print("\n🎉 Données de test ajoutées avec succès!")
        print("\n📊 Résumé:")
        print(f"   👔 Recruteurs: {len(recruiter_ids)}")
        print(f"   🏢 Entreprises: {len(company_ids)}")
        print(f"   💼 Offres: {jobs_added}")
        print(f"   👨‍🎓 Candidats: {candidates_added}")

        print("\n🚀 Vous pouvez maintenant:")
        print("   1. Visiter http://127.0.0.1:5000/jobs")
        print("   2. Tester la recherche et les filtres")
        print("   3. Uploader un CV pour voir le matching")
        print("   4. Tester les comptes recruteur/admin")

        return True

    except Exception as e:
        print(f"❌ Erreur lors de l'ajout des données de test: {e}")
        return False

if __name__ == "__main__":
    success = add_test_data()
    if success:
        print("\n✨ Prêt à explorer votre plateforme de recrutement IA!")
    else:
        print("\n❌ Échec de l'ajout des données de test")
        sys.exit(1)