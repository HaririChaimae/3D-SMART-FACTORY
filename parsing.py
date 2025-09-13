import os
import tempfile
import pytesseract
from PIL import Image
from pathlib import Path
import pdfplumber

# Fallback PDF reader
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


# Chemin vers Tesseract (si tu fais de l'OCR sur images)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- PDF ---
def extract_text_from_pdf(pdf_path, output_folder="mycv", output_file="resume.txt"):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        # Si le PDF est corrompu ou invalide, essayer avec PyPDF2 comme fallback
        if PYPDF2_AVAILABLE:
            try:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as e2:
                # Si les deux méthodes échouent, lever une erreur informative
                raise ValueError(f"Impossible de lire le PDF. Le fichier est peut-être corrompu ou n'est pas un PDF valide. Erreur: {str(e)}")
        else:
            raise ValueError(f"Impossible de lire le PDF. Le fichier est peut-être corrompu ou n'est pas un PDF valide. Erreur: {str(e)}")

    # Si aucun texte n'a été extrait, essayer l'OCR
    if not text.strip():
        try:
            # Convertir PDF en image et utiliser OCR
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path)
            for img in images:
                text += pytesseract.image_to_string(img, lang="eng") + "\n"
        except ImportError:
            pass  # pdf2image n'est pas installé
        except Exception as e:
            pass  # OCR a échoué

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
    try:
        import docx
    except ImportError:
        raise ValueError("La bibliothèque python-docx n'est pas installée. Installez-la avec: pip install python-docx")

    try:
        doc = docx.Document(docx_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
    except Exception as e:
        raise ValueError(f"Impossible de lire le fichier DOCX. Erreur: {str(e)}")

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
        try:
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
        except Exception as e:
            # Essayer de traiter comme texte brut si tout échoue
            try:
                with open(file_or_uploaded, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except:
                raise ValueError(f"Impossible de traiter le fichier {file_or_uploaded}. Erreur: {str(e)}")

    # Cas 2 : Si c'est un fichier Streamlit
    if hasattr(file_or_uploaded, "name") and hasattr(file_or_uploaded, "read"):
        suffix = Path(file_or_uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_or_uploaded.read())
            tmp_path = tmp.name

        try:
            # On appelle la même logique que pour les chemins
            return parse_cv(tmp_path)
        except Exception as e:
            # Essayer de lire comme texte brut
            try:
                file_or_uploaded.seek(0)  # Remettre au début
                content = file_or_uploaded.read()
                if isinstance(content, bytes):
                    return content.decode('utf-8', errors='ignore')
                return str(content)
            except:
                raise ValueError(f"Impossible de traiter le fichier uploadé. Erreur: {str(e)}")
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass

    # Sinon type inconnu
    raise TypeError("parse_cv attend un chemin (str) ou un UploadedFile Streamlit")
