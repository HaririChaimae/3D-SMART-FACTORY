# preprocessing.py

import re
import os
from dotenv import load_dotenv
from openrouter_client import extract_skills_from_cv

load_dotenv()

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else None

def extract_phone(text):
    match = re.search(r'(\+?\d[\d\s\-]{7,15})', text)
    return match.group(0) if match else None

def extract_name(text):
    """Extract name using OpenRouter for better accuracy"""
    try:
        from openrouter_client import openrouter_client

        if not openrouter_client.is_available():
            print("⚠️  OpenRouter not available - using fallback name extraction")
            return _fallback_name_extraction(text)

        prompt = f"""
        Extract the full name of the person from this CV/resume text.
        Return only the name, nothing else. If you can't find a clear name, return "Unknown".

        CV Text:
        {text[:2000]}  # Limit text to avoid token limits

        Instructions:
        - Look for the person's full name (first and last name)
        - Return only the name, no additional text
        - If multiple names appear, choose the most prominent one (usually at the top)
        - If no clear name is found, return "Unknown"
        """

        response = openrouter_client.generate_content(prompt, max_tokens=100)
        name = response.strip()

        # Clean up the response
        if name and name.lower() != "unknown" and len(name.split()) >= 1:
            print(f"✅ Name extracted: {name}")
            return name
        else:
            return _fallback_name_extraction(text)

    except Exception as e:
        print(f"LLM name extraction failed: {e}")
        return _fallback_name_extraction(text)

def _fallback_name_extraction(text):
    """Fallback method for name extraction"""
    lines = text.split('\n')

    # First, look for lines that look like full names (First Last format)
    for line in lines[:15]:
        line = line.strip()
        if line and not '@' in line and not line.startswith('http'):
            words = line.split()
            if len(words) == 2 and len(words[0]) > 1 and len(words[1]) > 1:
                # Check if it looks like a name (not a job title or header)
                if not any(header in line.lower() for header in ['experience', 'education', 'skills', 'contact', 'summary', 'objective', 'data', 'scientist', 'engineer', 'developer']):
                    return line

    # If no full name found, look for any line with 2+ words that's not a header
    for line in lines[:10]:
        line = line.strip()
        if line and not '@' in line and not line.startswith('http') and len(line.split()) >= 2:
            if not any(header in line.lower() for header in ['experience', 'education', 'skills', 'contact', 'summary', 'objective', 'data', 'scientist', 'engineer', 'developer']):
                return line

    return "Unknown"

def extract_skills(text):
    # Extended skill list with variations
    skill_variations = {
        "python": ["python", "py", "python programming", "python developer"],
        "java": ["java", "java programming", "java developer"],
        "javascript": ["javascript", "js", "node.js", "nodejs", "react", "angular", "vue.js", "vue", "jquery"],
        "sql": ["sql", "mysql", "postgresql", "postgres", "sqlite", "database", "databases"],
        "html": ["html", "html5", "css", "css3", "bootstrap", "frontend"],
        "machine learning": ["machine learning", "ml", "ai", "artificial intelligence", "tensorflow", "pytorch", "deep learning", "neural networks"],
        "aws": ["aws", "amazon web services", "cloud", "azure", "gcp", "google cloud"],
        "docker": ["docker", "kubernetes", "k8s", "container", "containers"],
        "git": ["git", "github", "version control", "svn"],
        "linux": ["linux", "unix", "bash", "shell scripting"],
        "c++": ["c++", "cpp", "c/c++"],
        "c#": ["c#", "csharp", ".net"],
        "php": ["php", "laravel", "symfony"],
        "ruby": ["ruby", "rails", "ruby on rails"],
        "go": ["go", "golang"],
        "rust": ["rust", "systems programming"],
        "swift": ["swift", "ios", "mobile development"],
        "kotlin": ["kotlin", "android"],
        "typescript": ["typescript", "ts"],
        "graphql": ["graphql", "api", "rest api", "rest"],
        "django": ["django", "flask", "web framework", "backend"],
        "spring": ["spring", "java spring", "microservices"],
        "mongodb": ["mongodb", "nosql", "redis", "cassandra"],
        "penetration testing": ["penetration testing", "pentest", "security", "cybersecurity", "network security"],
        "nlp": ["nlp", "natural language processing", "text mining", "computational linguistics"]
    }

    found_skills = set()
    text_lower = text.lower()

    for canonical_skill, variations in skill_variations.items():
        for variation in variations:
            if variation in text_lower:
                found_skills.add(canonical_skill)
                break

    return list(found_skills)

def preprocess_cv(cv_text: str):
    """
    Transforme le texte brut en dictionnaire structuré
    Utilise OpenRouter pour une extraction avancée des compétences
    """
    try:
        # Essayer d'abord l'extraction avancée avec OpenRouter
        advanced_data = extract_skills_from_cv(cv_text)

        # Compléter avec les informations de base
        data = {
            "name": extract_name(cv_text),
            "email": extract_email(cv_text),
            "phone": extract_phone(cv_text),
            "skills": advanced_data.get("skills", []),
            "programming_languages": advanced_data.get("programming_languages", []),
            "frameworks": advanced_data.get("frameworks", []),
            "tools": advanced_data.get("tools", []),
            "experience_years": advanced_data.get("experience_years", 0),
            "education_level": advanced_data.get("education_level", "Unknown"),
            "experience": [],  # TODO: extraction plus fine
            "education": []    # TODO: extraction plus fine
        }

        print(f"✅ CV preprocessé avec IA: {len(data['skills'])} compétences extraites")
        return data

    except Exception as e:
        print(f"⚠️  Erreur extraction IA: {e}")
        print("🔄 Utilisation de l'extraction basique...")

        # Fallback vers l'extraction basique
        data = {
            "name": extract_name(cv_text),
            "email": extract_email(cv_text),
            "phone": extract_phone(cv_text),
            "skills": extract_skills(cv_text),
            "programming_languages": [],
            "frameworks": [],
            "tools": [],
            "experience_years": 0,
            "education_level": "Unknown",
            "experience": [],
            "education": []
        }

        print(f"✅ CV preprocessé (fallback): {len(data['skills'])} compétences extraites")
        return data
