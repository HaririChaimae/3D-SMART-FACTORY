# preprocessing.py

import re
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GEN_MODEL = "gemini-1.5-flash"
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else None

def extract_phone(text):
    match = re.search(r'(\+?\d[\d\s\-]{7,15})', text)
    return match.group(0) if match else None

def extract_name(text):
    """Extract name using LLM for better accuracy"""
    try:
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

        model = genai.GenerativeModel(GEN_MODEL)
        response = model.generate_content(prompt)
        name = response.text.strip()

        # Clean up the response
        if name and name.lower() != "unknown" and len(name.split()) >= 1:
            return name
        else:
            return "Unknown"

    except Exception as e:
        print(f"LLM name extraction failed: {e}")
        # Fallback to heuristic method
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
    common_skills = [
        "Python", "Java", "C++", "C#", "SQL", "JavaScript", "React", "Angular", "Vue.js",
        "Django", "Flask", "Spring", "Node.js", "Express", "AWS", "Azure", "GCP",
        "Docker", "Kubernetes", "Git", "Linux", "Windows", "MySQL", "PostgreSQL",
        "MongoDB", "Redis", "HTML", "CSS", "Bootstrap", "jQuery", "PHP", "Ruby",
        "Go", "Rust", "Swift", "Kotlin", "TypeScript", "GraphQL", "REST API",
        "Machine Learning", "AI", "Data Science", "TensorFlow", "PyTorch"
    ]
    found = [skill for skill in common_skills if skill.lower() in text.lower()]
    return found

def preprocess_cv(cv_text: str):
    """
    Transforme le texte brut en dictionnaire structuré
    """
    data = {
        "name": extract_name(cv_text),
        "email": extract_email(cv_text),
        "phone": extract_phone(cv_text),
        "skills": extract_skills(cv_text),
        "experience": [],  # TODO: extraction plus fine
        "education": []    # TODO: extraction plus fine
    }

    return data
