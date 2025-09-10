import os
import tempfile
import pytesseract
from PIL import Image
from pathlib import Path 
import pdfplumber 


# Chemin vers Tesseract (si tu fais de l'OCR sur images)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- PDF ---
def extract_text_from_pdf(pdf_path, output_folder="mycv", output_file="resume.txt"):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    # Créer le dossier s'il n'existe pas
    os.makedirs(output_folder, exist_ok=True)

    # Chemin de sortie
    output_path = os.path.join(output_folder, output_file)

    # Sauvegarder le texte dans un fichier
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Le CV a été enregistré dans : {output_path}")
    return text

# --- Image ---
def extract_text_from_image(image_path):
    img = Image.open(image_path)
    return pytesseract.image_to_string(img, lang="eng")

# --- DOCX ---
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])

# --- Fonction unifiée ---
def parse_cv(file_or_uploaded):
    """
    Gère à la fois :
      - Un chemin classique (str)
      - Un objet UploadedFile venant de Streamlit
    """
    # Cas 1 : Si c'est déjà un chemin string
    if isinstance(file_or_uploaded, str):
        ext = Path(file_or_uploaded).suffix.lower()
        if ext == ".pdf":
            return extract_text_from_pdf(file_or_uploaded)
        elif ext in (".png", ".jpg", ".jpeg"):
            return extract_text_from_image(file_or_uploaded)
        elif ext == ".docx":
            return extract_text_from_docx(file_or_uploaded)
        elif ext == ".txt":
            with open(file_or_uploaded, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Format non supporté: {ext}")

    # Cas 2 : Si c'est un fichier Streamlit
    if hasattr(file_or_uploaded, "name") and hasattr(file_or_uploaded, "read"):
        suffix = Path(file_or_uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_or_uploaded.read())
            tmp_path = tmp.name

        try:
            # On appelle la même logique que pour les chemins
            return parse_cv(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass

    # Sinon type inconnu
    raise TypeError("parse_cv attend un chemin (str) ou un UploadedFile Streamlit")
