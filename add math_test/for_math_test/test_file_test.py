#!/usr/bin/env python3
"""
TEST FILE: Complete Recruitment System Test Process
===============================================

This file demonstrates the complete process of taking a technical test in the recruitment system.
It shows the flow from question generation to answer evaluation using the same data folder structure.

Process Flow:
1. Load knowledge base from PDF files in data/ folder
2. Generate technical questions from the knowledge base
3. Simulate candidate answers
4. Evaluate answers using AI agent
5. Calculate and display scores

Author: Kilo Code
Date: 2025-09-11
"""

import os
import sys
import json
import time
import base64
from datetime import datetime
from io import BytesIO

# Set console encoding to handle French characters
if sys.platform == 'win32':
    try:
        import os
        # Set environment variables for UTF-8 encoding
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'
        # Try to set console code page
        os.system('chcp 65001 >nul 2>&1')
    except Exception as e:
        # If encoding setup fails, continue without it
        pass

# Add current directory to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import system modules
from preprocessing import preprocess_cv
from matching import match_jobs
from agent import (
    generate_answer_for_question,
    evaluate_answers,
    build_vector_store,
    search_knowledge,
    extract_text_from_pdf
)
from parsing import parse_cv
import google.generativeai as genai
import re
import logging

# Try to import PDF image extraction libraries
try:
    from PyPDF2 import PdfReader
    from PIL import Image
    import fitz  # PyMuPDF for better image extraction
    PDF_IMAGE_SUPPORT = True
except ImportError:
    PDF_IMAGE_SUPPORT = False
    print("Warning: PDF image extraction libraries not available. Install PyMuPDF and Pillow for full functionality.")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables (you may need to set these)
os.environ.setdefault('GOOGLE_API_KEY', 'AIzaSyDK1Cf0L83xGY1RtQ20dLMGeklCOyMZuJQ')

# Configure Gemini model
GEN_MODEL = "gemini-1.5-flash"

def setup_gemini():
    """Setup Google Gemini API"""
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set. Some features may not work.")
            return False

        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        logger.error(f"Failed to setup Gemini API: {e}")
        return False

def get_pdf_files_info(data_folder="data_test"):
    """Get info about PDF files in specified data folder"""
    pdf_files = []
    if os.path.exists(data_folder):
        for file_name in os.listdir(data_folder):
            if file_name.lower().endswith('.pdf'):
                file_path = os.path.join(data_folder, file_name)
                pdf_files.append({
                    'name': file_name,
                    'size': os.path.getsize(file_path),
                    'mtime': os.path.getmtime(file_path)
                })
    return pdf_files

def map_job_to_data_folder(job_matching_result):
    """
    Map job matching result to appropriate data folder.
    Returns the folder path based on job type.
    """
    if not job_matching_result or job_matching_result == "No suitable job found":
        return "for_math_test/data_test"  # Default fallback

    job_title = job_matching_result.lower()

    # Map job titles to data folders
    if any(keyword in job_title for keyword in ['data science', 'data scientist', 'machine learning', 'ai', 'artificial intelligence']):
        return "for_math_test/data/data_science"
    elif any(keyword in job_title for keyword in ['mathematician', 'mathematics', 'math', 'statistics', 'analyst']):
        return "for_math_test/data/Mathematician"
    else:
        return "for_math_test/data_test"  # Default fallback

def extract_images_from_pdf(pdf_path):
    """Extract images from PDF and return as base64 encoded strings"""
    if not PDF_IMAGE_SUPPORT:
        return []

    images = []
    try:
        # Use PyMuPDF for better image extraction
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Convert to base64
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                image_data_url = f"data:image/{image_ext};base64,{image_base64}"

                images.append({
                    'page': page_num + 1,
                    'index': img_index,
                    'data_url': image_data_url,
                    'extension': image_ext
                })

        doc.close()

    except Exception as e:
        logger.error(f"Error extracting images from PDF: {e}")
        # Fallback to basic image extraction if PyMuPDF fails
        try:
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages):
                if "/Resources" in page and "/XObject" in page["/Resources"]:
                    x_object = page["/Resources"]["/XObject"]
                    for obj_name in x_object:
                        obj = x_object[obj_name]
                        if obj["/Subtype"] == "/Image":
                            img_data = obj._data
                            image_base64 = base64.b64encode(img_data).decode('utf-8')
                            images.append({
                                'page': page_num + 1,
                                'index': len(images),
                                'data_url': f"data:image/png;base64,{image_base64}",
                                'extension': 'png'
                            })
        except Exception as e2:
            logger.error(f"Fallback image extraction also failed: {e2}")

    return images

def display_image_in_terminal(image_data_url, width=50):
    """Display image in terminal (basic ASCII representation)"""
    try:
        # Check if it's a URL (starts with http/https)
        if image_data_url.startswith(('http://', 'https://')):
            print(f"[IMAGE] IMAGE URL: {image_data_url}")
            print(f"[INFO] To view the image, copy and paste this URL into your browser:")
            print(f"       {image_data_url}")
            print(f"[LINK] Click to open: {image_data_url}")
            return

        # For base64 images (from PDFs)
        if ',' in image_data_url:
            header, encoded = image_data_url.split(",", 1)
            image_data = base64.b64decode(encoded)

            # For terminal display, we'll show image info
            print(f"[IMAGE] Image detected ({len(image_data)} bytes)")
            print(f"[IMAGE] Data URL: {image_data_url[:100]}...")
        else:
            print(f"[IMAGE] Image URL: {image_data_url}")

    except Exception as e:
        print(f"[ERROR] Could not display image: {e}")
        print(f"[INFO] Image URL: {image_data_url}")

def build_vector_store_cached(pdf_files_info):
    """Build vector store from PDF files"""
    if not pdf_files_info:
        logger.warning("No PDF files found in data folder")
        return None, []

    logger.info('Building vector store from PDF files...')
    try:
        index, texts = build_vector_store()
        if index is None:
            logger.error("Failed to build vector store")
            return None, []

        logger.info(f'Vector store built with {len(texts)} documents')
        return index, texts
    except Exception as e:
        logger.error(f"Error building vector store: {e}")
        return None, []

def extract_text_with_page_info(pdf_path):
    """Extract text from PDF with page information, links, and embedded URLs"""
    try:
        import fitz
        import re
        doc = fitz.open(pdf_path)
        pages_content = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()

            # Extract links from the page structure
            structural_links = []
            for link in page.get_links():
                link_info = {
                    'page': page_num + 1,
                    'rect': link.get('from', {}),
                }

                if link.get('uri'):
                    link_info['uri'] = link['uri']
                    link_info['type'] = 'external'
                elif link.get('page'):
                    link_info['target_page'] = link['page'] + 1  # Convert to 1-based
                    link_info['type'] = 'internal'
                else:
                    link_info['type'] = 'unknown'

                structural_links.append(link_info)

            # Extract URLs from text content using regex
            text_links = []
            url_patterns = [
                r'https?://[^\s<>"{}|\\^`\[\]]+',  # Standard URLs
                r'http?://[^\s<>"{}|\\^`\[\]]+',   # HTTP URLs
                r'www\.[^\s<>"{}|\\^`\[\]]+',      # WWW URLs
                r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s<>"{}|\\^`\[\]]*'  # Domain-based URLs
            ]

            for pattern in url_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Clean up the URL
                    url = match.strip('.,;:!?')
                    if url and len(url) > 10:  # Filter out very short matches
                        text_links.append({
                            'uri': url,
                            'type': 'text_embedded',
                            'page': page_num + 1,
                            'context': text[max(0, text.find(url)-50):text.find(url)+len(url)+50]  # Context around URL
                        })

            # Combine structural and text links
            all_links = structural_links + text_links

            # Get image information
            images_info = []
            for img_index, img in enumerate(page.get_images(full=True)):
                images_info.append({
                    'index': img_index,
                    'xref': img[0],
                    'page': page_num + 1
                })

            if text.strip() or all_links or images_info:
                pages_content.append({
                    'page': page_num + 1,
                    'text': text.strip(),
                    'links': all_links,
                    'images': images_info,
                    'has_images': len(images_info) > 0
                })

        doc.close()
        return pages_content
    except Exception as e:
        logger.error(f"Error extracting text with page info: {e}")
        return []

def analyze_link_image_relationships(pages_content):
    """Analyze relationships between links and images on the same pages"""
    link_image_map = {}

    for page_info in pages_content:
        page_num = page_info['page']
        links = page_info.get('links', [])
        images = page_info.get('images', [])

        # Create mapping between links and images
        for link in links:
            if 'uri' in link:
                uri = link['uri'].lower()

                # Check if URI is an image URL (common image hosting services)
                is_image_url = any(domain in uri for domain in [
                    'postimg.cc', 'imgur.com', 'photobucket.com', 'flickr.com',
                    'pinterest.com', 'instagram.com', 'imgbb.com', 'image.png',
                    'image.jpg', 'image.jpeg', 'image.gif', 'image.webp'
                ]) or any(ext in uri for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])

                if is_image_url or any(keyword in uri for keyword in ['image', 'img', 'figure', 'chart', 'graph', 'diagram', 'photo']):
                    # Create a virtual image object for text-embedded URLs
                    virtual_image = {
                        'index': len(images),  # Next available index
                        'xref': f"text_link_{len(link_image_map)}",  # Unique identifier
                        'page': page_num,
                        'is_virtual': True,
                        'url': link['uri'],
                        'type': link.get('type', 'text_embedded'),
                        'extension': 'png' if '.png' in uri else ('jpg' if '.jpg' in uri or '.jpeg' in uri else 'unknown')
                    }

                    link_key = f"page_{page_num}_link_{len(link_image_map)}"
                    link_image_map[link_key] = {
                        'link': link,
                        'image': virtual_image,
                        'page': page_num,
                        'relationship': 'text_embedded_image_url' if link.get('type') == 'text_embedded' else 'structural_image_link'
                    }

                # Also check for actual images on the same page
                elif images:
                    for img in images:
                        link_key = f"page_{page_num}_img_{len(link_image_map)}"
                        link_image_map[link_key] = {
                            'link': link,
                            'image': img,
                            'page': page_num,
                            'relationship': 'same_page_structural'
                        }

    return link_image_map

def extract_image_urls_from_text(text):
    """Extract image URLs from text content"""
    logger.info(f"Extracting URLs from text: {text[:100]}...")

    url_patterns = [
        r'https?://[^\s<>"{}|\\^`\[\]]+',  # Standard URLs
        r'http?://[^\s<>"{}|\\^`\[\]]+',   # HTTP URLs
    ]

    image_urls = []
    for pattern in url_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        logger.info(f"Pattern '{pattern}' found matches: {matches}")
        for match in matches:
            url = match.strip('.,;:!?')
            logger.info(f"Processing URL: {url}")
            if url and len(url) > 10:
                # Check if it's an image URL
                is_image_url = any(domain in url.lower() for domain in [
                    'postimg.cc', 'imgur.com', 'photobucket.com', 'flickr.com',
                    'pinterest.com', 'instagram.com', 'imgbb.com'
                ]) or any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])

                logger.info(f"URL '{url}' is image URL: {is_image_url}")
                if is_image_url:
                    image_urls.append(url)

    logger.info(f"Final image URLs found: {image_urls}")
    return image_urls

def associate_images_with_exercises(exercises, images, pages_content, link_image_relationships=None):
    """Associate images with exercises based on links and page content"""
    exercise_image_map = {}

    for i, exercise in enumerate(exercises):
        exercise_images = []
        exercise_text = exercise.lower()
        logger.info(f"Exercise {i+1} text preview: {exercise_text[:200]}...")

        # Extract image URLs directly from the exercise text
        print(f"DEBUG: Processing exercise {i+1}: {exercise[:100]}...")
        exercise_image_urls = extract_image_urls_from_text(exercise)
        print(f"DEBUG: Found {len(exercise_image_urls)} image URLs in exercise {i+1}: {exercise_image_urls}")
        logger.info(f"Found {len(exercise_image_urls)} image URLs in exercise {i+1}: {exercise_image_urls}")

        # Create virtual images for URLs found in the exercise text
        for url in exercise_image_urls:
            virtual_image = {
                'page': 1,  # Default page
                'index': 0,
                'data_url': url,
                'extension': 'png' if '.png' in url.lower() else ('jpg' if '.jpg' in url.lower() or '.jpeg' in url.lower() else 'unknown'),
                'is_virtual': True,
                'url': url
            }
            exercise_images.append(virtual_image)
            logger.info(f"Created virtual image for exercise {i+1} from URL: {url}")

        # If no URLs found in exercise text, try the original logic
        if not exercise_images:
            # First priority: Direct link-image relationships from embedded URLs
            if link_image_relationships:
                for rel_key, relationship in link_image_relationships.items():
                    link = relationship['link']
                    img = relationship['image']

                    # Check if this is a text-embedded image URL
                    if link.get('type') == 'text_embedded' and 'uri' in link:
                        link_uri = link['uri']

                        # Check if URI is an image URL
                        is_image_url = any(domain in link_uri for domain in [
                            'postimg.cc', 'imgur.com', 'photobucket.com', 'flickr.com',
                            'pinterest.com', 'instagram.com', 'imgbb.com'
                        ]) or any(ext in link_uri for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])

                        if is_image_url:
                            # Only associate if the URL is mentioned in the exercise text (with or without https://)
                            link_uri_lower = link_uri.lower()
                            logger.info(f"Checking association for exercise {i+1}: URL '{link_uri}' in exercise text: {link_uri_lower in exercise_text}")
                            if link_uri_lower in exercise_text or link_uri_lower.replace('https://', '') in exercise_text:
                                # Convert virtual image to proper format for display
                                virtual_image = {
                                    'page': img['page'],
                                    'index': img['index'],
                                    'data_url': link['uri'],  # Use the URL as data_url for web display
                                    'extension': img.get('extension', 'png'),
                                    'is_virtual': True,
                                    'url': link['uri']
                                }
                                exercise_images.append(virtual_image)
                                logger.info(f"Associated specific virtual image from URL: {link['uri']} with exercise {i+1}")

            # Second priority: Regular PDF images with link associations
            for img in images:
                img_page = img['page']
                should_include = False

                # Check for link-based associations
                if link_image_relationships:
                    for rel_key, relationship in link_image_relationships.items():
                        if (relationship['image']['page'] == img_page and
                            relationship['image']['xref'] == img.get('xref')):
                            link_uri = relationship['link'].get('uri', '').lower()
                            if any(keyword in link_uri for keyword in ['image', 'img', 'figure', 'chart', 'graph']):
                                if any(keyword in exercise_text for keyword in ['graph', 'chart', 'figure', 'diagram', 'image', 'table', 'voir', 'consulter']):
                                    should_include = True
                                    break

                # Third priority: Content-based matching
                if not should_include:
                    for page_info in pages_content:
                        if page_info['page'] == img_page:
                            page_text = page_info['text'].lower()
                            # Check if page content relates to exercise content
                            if any(keyword in page_text for keyword in ['graph', 'chart', 'figure', 'diagram', 'image', 'table']):
                                if any(keyword in exercise_text for keyword in ['graph', 'chart', 'figure', 'diagram', 'image', 'table']):
                                    should_include = True
                                    break

                # Fourth priority: Page number references in exercise
                if not should_include:
                    # Extract page numbers mentioned in the exercise
                    import re
                    page_numbers = re.findall(r'page\s*(\d+)', exercise_text, re.IGNORECASE)
                    if str(img_page) in page_numbers:
                        should_include = True

                if should_include:
                    exercise_images.append(img)

            # If no specific images found, try to find image URLs mentioned in the exercise text
            if not exercise_images:
                # Look for image URLs directly in the exercise text
                exercise_text_lower = exercise.lower()
                for page_info in pages_content:
                    for link in page_info.get('links', []):
                        if link.get('type') == 'text_embedded' and 'uri' in link:
                            uri = link['uri'].lower()
                            is_image_url = any(domain in uri for domain in [
                                'postimg.cc', 'imgur.com', 'photobucket.com', 'flickr.com',
                                'pinterest.com', 'instagram.com', 'imgbb.com'
                            ]) or any(ext in uri for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])

                            if is_image_url:
                                # Check if this specific URI is directly mentioned in the exercise text
                                # Only associate if the exact URL appears in the exercise
                                if link['uri'] in exercise_text:
                                    virtual_image = {
                                        'page': page_info['page'],
                                        'index': 0,
                                        'data_url': link['uri'],
                                        'extension': 'png' if '.png' in uri else ('jpg' if '.jpg' in uri or '.jpeg' in uri else 'unknown'),
                                        'is_virtual': True,
                                        'url': link['uri']
                                    }
                                    exercise_images.append(virtual_image)
                                    logger.info(f"Associated specific virtual image from URL: {link['uri']} with exercise {i+1}")
                                    break
                    if exercise_images:
                        break

        exercise_image_map[exercise] = exercise_images

    return exercise_image_map

def generate_exercises_from_pdf(pdf_path, num_exercises=2):
    """Generate multiple exercises from a specific PDF file with image support"""
    try:
        # Extract text with page information
        pages_content = extract_text_with_page_info(pdf_path)

        # Extract images from PDF
        images = extract_images_from_pdf(pdf_path)

        if not pages_content:
            logger.warning(f"No text found in PDF: {pdf_path}")
            return [], {}, []

        # Create context from PDF text with page references
        context_parts = []
        for page_info in pages_content:
            context_parts.append(f"Page {page_info['page']}: {page_info['text'][:1000]}...")
        context = "\n\n".join(context_parts)[:4000]

        # Add image information to context
        if images:
            image_info = "\nImages found on pages: " + ", ".join([f"Page {img['page']}" for img in images])
            context += image_info

        prompt = f"""
        Voici le contenu d'un document PDF technique avec informations de pages :
        {context}

        Générez {num_exercises} exercices pratiques différents en français basés sur ce contenu.

        Chaque exercice doit suivre exactement ce format :

        Exercice : [Titre clair et court]
        Description : [Explication complète de la tâche, avec détails sur les entrées, sorties attendues,
        et contraintes éventuelles. Rédigez comme une consigne d'énoncé détaillée.]

        ⚠️ Contraintes importantes :
        - Générez UNIQUEMENT {num_exercises} exercices (pas plus, pas moins)
        - Séparez chaque exercice par une ligne vide
        - Ne mettez pas de numérotation automatique (pas de 1., 2., etc.)
        - Ne répondez qu'avec les exercices, rien d'autre
        - N'utilisez pas de saisie avec input(). Les exercices doivent définir les valeurs d'entrée sous forme
        de variables ou de paramètres déjà fournis, jamais par interaction utilisateur.
        - CRITIQUEMENT IMPORTANT : Chaque exercice doit référencer UNIQUEMENT UNE SEULE image/diagramme spécifique
        - Si vous référencez une image, utilisez l'URL exacte trouvée dans le contenu (ex: "voir https://i.postimg.cc/xxxxx/image.png")
        - Ne référencez pas plusieurs images dans le même exercice
        - Distribuez les images disponibles entre les différents exercices de manière équilibrée
        - Si le contenu fait référence à des graphiques, tableaux, ou figures, mentionnez
        qu'il faut consulter l'image correspondante sur la page appropriée
        - Assurez-vous que les exercices sont variés et couvrent différents aspects du contenu
        - Chaque exercice doit être complètement indépendant des autres
        - Priorisez les exercices qui peuvent bénéficier des images/diagrammes disponibles
        """

        model = genai.GenerativeModel(GEN_MODEL)
        response = model.generate_content(prompt)
        exercises_text = response.text.strip()

        # Split exercises by looking for "Exercice :" pattern
        exercises = re.split(r'(?=Exercice\s*:)', exercises_text)
        exercises = [ex.strip() for ex in exercises if ex.strip()]

        # Clean up each exercise
        cleaned_exercises = []
        for exercise in exercises:
            # Remove leading non-word chars and clean up Unicode issues
            exercise = re.sub(r'^[^\w]*', '', exercise)
            # Remove zero-width spaces and other problematic Unicode chars
            exercise = exercise.replace('\u200b', '').replace('\ufeff', '')
            # Normalize other Unicode characters
            exercise = exercise.encode('utf-8', errors='ignore').decode('utf-8')
            exercise = exercise.strip()
            if exercise:
                cleaned_exercises.append(exercise)

        if not cleaned_exercises:
            logger.error("No valid exercises generated")
            return [], {}, []

        # Analyze link-image relationships
        link_image_relationships = analyze_link_image_relationships(pages_content)
        logger.info(f"Found {len(link_image_relationships)} link-image relationships")

        # Debug: Log found URLs
        for key, rel in link_image_relationships.items():
            logger.info(f"Found URL in PDF: {rel['link']['uri']}")

        # Associate images with exercises
        exercise_image_map = associate_images_with_exercises(cleaned_exercises, images, pages_content, link_image_relationships)

        logger.info(f"Generated {len(cleaned_exercises)} exercises from PDF: {pdf_path}")
        return cleaned_exercises[:num_exercises], exercise_image_map, images

    except Exception as e:
        logger.error(f"Error generating exercises from PDF {pdf_path}: {e}")
        return [], {}, []

def extract_exercises_from_pdf(pdf_path):
    """Extract exercises and their corrections from the PDF"""
    try:
        # Extract text with page information
        pages_content = extract_text_with_page_info(pdf_path)

        if not pages_content:
            logger.warning(f"No text found in PDF: {pdf_path}")
            return [], {}

        # Combine all text
        full_text = "\n".join([page['text'] for page in pages_content])

        # Split exercises based on "Exercice" pattern
        exercises = []
        corrections = {}

        # Find all exercises
        exercise_pattern = r'(Exercice\s+\d+.*?)(?=Exercice\s+\d+|Correction|$)'
        matches = re.findall(exercise_pattern, full_text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            exercise_text = match.strip()
            if exercise_text:
                # Clean Unicode characters
                exercise_text = exercise_text.replace('\u200b', '').replace('\ufeff', '').replace('\u2705', '').replace('\u2713', '')
                # Remove other common Unicode symbols that might cause issues
                exercise_text = re.sub(r'[^\x00-\x7F]+', '', exercise_text)
                exercises.append(exercise_text)

                # Try to find corresponding correction
                exercise_num = re.search(r'Exercice\s+(\d+)', exercise_text, re.IGNORECASE)
                if exercise_num:
                    num = exercise_num.group(1)
                    correction_pattern = rf'Correction.*?Exercice\s*{num}[:\s]*(.*?)(?=Exercice\s+\d+|$)'
                    correction_match = re.search(correction_pattern, full_text, re.DOTALL | re.IGNORECASE)

                    if correction_match:
                        corrections[exercise_text] = correction_match.group(1).strip()
                    else:
                        corrections[exercise_text] = "Correction non trouvée dans le PDF"

        logger.info(f"Extracted {len(exercises)} exercises from PDF")
        return exercises, corrections

    except Exception as e:
        logger.error(f"Error extracting exercises from PDF: {e}")
        return [], {}

def rag_answer_exercise(exercise_text, pdf_path):
    """Use RAG to extract the correct answer for a specific exercise from the PDF"""
    try:
        # Extract exercises and corrections from PDF
        exercises, corrections = extract_exercises_from_pdf(pdf_path)

        # Find the matching exercise
        best_match = None
        best_score = 0

        for extracted_exercise in exercises:
            # Simple similarity check (could be improved with embeddings)
            exercise_words = set(exercise_text.lower().split())
            extracted_words = set(extracted_exercise.lower().split())
            similarity = len(exercise_words.intersection(extracted_words)) / len(exercise_words.union(extracted_words))

            if similarity > best_score:
                best_score = similarity
                best_match = extracted_exercise

        if best_match and best_score > 0.3:  # Threshold for matching
            return corrections.get(best_match, "Correction non trouvée")
        else:
            # Fallback to RAG search
            pdf_files_info = get_pdf_files_info()
            if pdf_files_info:
                index, texts = build_vector_store_cached(pdf_files_info)
                if index and texts:
                    return generate_answer_for_question(exercise_text, index, texts)

            return "Impossible d'extraire la réponse du PDF"

    except Exception as e:
        logger.error(f"Error in RAG answer extraction: {e}")
        return f"Erreur RAG: {e}"

def generate_interview_content(num_exercises=2, job_matching_result=None):
    """Generate multiple interview questions and correct answers from PDF with images"""
    logger.info(f"Generating {num_exercises} interview exercises with image support...")

    # Determine which data folder to use based on job matching
    if job_matching_result:
        data_folder = map_job_to_data_folder(job_matching_result)
        logger.info(f"Using data folder '{data_folder}' for job matching: {job_matching_result}")
    else:
        data_folder = "for_math_test/data_test"  # Default fallback
        logger.info("No job matching provided, using default data_test folder")

    # Get PDF files info from the appropriate folder
    pdf_files_info = get_pdf_files_info(data_folder)

    if not pdf_files_info:
        logger.warning(f"No PDF files found in {data_folder}, using fallback exercises")
        fallback_exercises = [
            "Exercice : Températures de Bordeaux\nDescription : En consultant le graphique des températures moyennes à Bordeaux disponible à l'adresse https://i.postimg.cc/bv5dhNBF/image.png, déterminez la différence de température moyenne entre le mois le plus chaud et le mois le plus froid. Indiquez également le nombre de mois où la température moyenne est inférieure à 15°C.",
            "Exercice : Plus court chemin avec Dijkstra\nDescription : Considérant le graphe pondéré orienté présenté à l'adresse https://i.postimg.cc/m25FZWvb/89-F47418-93-C5-4-E90-A05-D-BB75-CECA15-CC.png, appliquez l'algorithme de Dijkstra pour trouver le plus court chemin et son coût depuis le sommet 'a' jusqu'au sommet 'c'."
        ]
        fallback_answers = {
            fallback_exercises[0]: "Fonction de calcul de somme",
            fallback_exercises[1]: "Fonction de calcul de moyenne"
        }
        return fallback_exercises[:num_exercises], {k: v for k, v in fallback_answers.items() if k in fallback_exercises[:num_exercises]}, {}, []

    # Find the specific PDF file in the selected data folder
    target_pdf = None
    for pdf_info in pdf_files_info:
        pdf_name = pdf_info['name'].lower()
        # Look for relevant PDF files in the selected folder
        if any(keyword in pdf_name for keyword in ['test_data', 'maths', 'exercice', 'it_exercices', 'pdf']):
            target_pdf = os.path.join(data_folder, pdf_info['name'])
            logger.info(f"Found target PDF: {pdf_info['name']} in folder {data_folder}")
            break

    # If no specific PDF found, use the first available PDF in the selected folder
    if not target_pdf and pdf_files_info:
        target_pdf = os.path.join(data_folder, pdf_files_info[0]['name'])
        logger.info(f"Using first available PDF: {pdf_files_info[0]['name']} in folder {data_folder}")

    if not target_pdf:
        logger.error("No suitable PDF found")
        return [], {}, []

    logger.info(f"Using PDF file: {target_pdf}")

    # First try to extract existing exercises from PDF
    extracted_exercises, extracted_corrections = extract_exercises_from_pdf(target_pdf)

    if extracted_exercises and len(extracted_exercises) >= num_exercises:
        # Use extracted exercises
        exercises = extracted_exercises[:num_exercises]
        correct_answers = {ex: extracted_corrections.get(ex, "Correction non trouvée") for ex in exercises}

        # Process exercises through image association
        pages_content = extract_text_with_page_info(target_pdf)
        images = extract_images_from_pdf(target_pdf)
        link_image_relationships = analyze_link_image_relationships(pages_content)
        exercise_image_map = associate_images_with_exercises(exercises, images, pages_content, link_image_relationships)
        all_images = images

        logger.info(f"Using {len(exercises)} extracted exercises from PDF")
    else:
        # Generate new exercises from the specific PDF
        exercises, exercise_image_map, all_images = generate_exercises_from_pdf(target_pdf, num_exercises)

        if not exercises:
            logger.warning("Failed to generate exercises, using fallback")
            fallback_exercises = [
                "Exercice : Températures de Bordeaux\nDescription : En consultant le graphique des températures moyennes à Bordeaux disponible à l'adresse https://i.postimg.cc/bv5dhNBF/image.png, déterminez la différence de température moyenne entre le mois le plus chaud et le mois le plus froid. Indiquez également le nombre de mois où la température moyenne est inférieure à 15°C.",
                "Exercice : Plus court chemin avec Dijkstra\nDescription : Considérant le graphe pondéré orienté présenté à l'adresse https://i.postimg.cc/m25FZWvb/89-F47418-93-C5-4-E90-A05-D-BB75-CECA15-CC.png, appliquez l'algorithme de Dijkstra pour trouver le plus court chemin et son coût depuis le sommet 'a' jusqu'au sommet 'c'."
            ]
            exercises = fallback_exercises[:num_exercises]

            # Process fallback exercises through image association
            pages_content = extract_text_with_page_info(target_pdf) if target_pdf else []
            images = extract_images_from_pdf(target_pdf) if target_pdf else []
            link_image_relationships = analyze_link_image_relationships(pages_content)
            exercise_image_map = associate_images_with_exercises(exercises, images, pages_content, link_image_relationships)
    
            # For fallback exercises, manually associate images since URLs are embedded in text
            if not exercise_image_map or all(not imgs for imgs in exercise_image_map.values()):
                exercise_image_map = {}
                for i, exercise in enumerate(exercises):
                    if "https://i.postimg.cc/bv5dhNBF/image.png" in exercise:
                        exercise_image_map[exercise] = [{
                            'page': 1, 'index': 0,
                            'data_url': 'https://i.postimg.cc/bv5dhNBF/image.png',
                            'extension': 'png', 'is_virtual': True,
                            'url': 'https://i.postimg.cc/bv5dhNBF/image.png'
                        }]
                    elif "https://i.postimg.cc/m25FZWvb/89-F47418-93-C5-4-E90-A05-D-BB75-CECA15-CC.png" in exercise:
                        exercise_image_map[exercise] = [{
                            'page': 1, 'index': 0,
                            'data_url': 'https://i.postimg.cc/m25FZWvb/89-F47418-93-C5-4-E90-A05-D-BB75-CECA15-CC.png',
                            'extension': 'png', 'is_virtual': True,
                            'url': 'https://i.postimg.cc/m25FZWvb/89-F47418-93-C5-4-E90-A05-D-BB75-CECA15-CC.png'
                        }]
                    else:
                        exercise_image_map[exercise] = []
    
            all_images = images

        # Generate correct answers for each exercise using RAG
        correct_answers = {}

        try:
            # Build vector store for answer generation
            index, texts = build_vector_store_cached(pdf_files_info)

            if index and texts:
                for exercise in exercises:
                    # Use RAG to extract answer from PDF
                    answer = rag_answer_exercise(exercise, target_pdf)
                    correct_answers[exercise] = answer
                logger.info(f"Generated RAG-based answers for {len(exercises)} exercises")
            else:
                for exercise in exercises:
                    correct_answers[exercise] = "Réponse basée sur les meilleures pratiques de programmation Python."

        except Exception as e:
            for exercise in exercises:
                correct_answers[exercise] = f"Erreur génération: {e}"
            logger.error(f"Error generating answers: {e}")

    return exercises, correct_answers, exercise_image_map, all_images

def simulate_candidate_answers(questions):
    """Simulate candidate providing answers to multiple exercises"""
    logger.info(f"Simulating candidate answers for {len(questions)} exercises...")

    # Sample answers for different types of exercises
    sample_answers = [
        """def calculer_somme(a, b):
    \"\"\"Calcule la somme de deux nombres\"\"\"
    return a + b

# Test de la fonction
if __name__ == "__main__":
    nombre1 = 5
    nombre2 = 3
    resultat = calculer_somme(nombre1, nombre2)
    print(f"La somme de {nombre1} et {nombre2} est: {resultat}")""",

        """def calculer_moyenne(liste_nombres):
    \"\"\"Calcule la moyenne d'une liste de nombres\"\"\"
    if not liste_nombres:
        return 0
    return sum(liste_nombres) / len(liste_nombres)

# Test de la fonction
if __name__ == "__main__":
    nombres = [10, 15, 20, 25, 30]
    moyenne = calculer_moyenne(nombres)
    print(f"La moyenne des nombres {nombres} est: {moyenne}")""",

        """def trouver_maximum(liste_nombres):
    \"\"\"Trouve le nombre maximum dans une liste\"\"\"
    if not liste_nombres:
        return None
    maximum = liste_nombres[0]
    for nombre in liste_nombres:
        if nombre > maximum:
            maximum = nombre
    return maximum

# Test de la fonction
if __name__ == "__main__":
    nombres = [5, 12, 8, 25, 3]
    max_val = trouver_maximum(nombres)
    print(f"Le maximum dans {nombres} est: {max_val}")"""
    ]

    user_answers = {}
    for i, exercise in enumerate(questions):
        # Use different sample answers for different exercises
        answer_index = i % len(sample_answers)
        user_answers[exercise] = sample_answers[answer_index]
        logger.info(f"Provided sample answer for exercise {i+1}")

    return user_answers

def run_complete_test_process(num_exercises=2):
    """Run the complete test process with multiple exercises and image support"""
    print("=" * 80)
    print(f"MULTIPLE EXERCISES TEST PROCESS WITH IMAGE SUPPORT ({num_exercises} EXERCISES)")
    print("=" * 80)
    print()

    start_time = time.time()

    # Step 1: Setup
    print("STEP 1: System Setup")
    print("-" * 40)

    # Check data_test folder
    if os.path.exists("for_math_test/data_test"):
        pdf_files = get_pdf_files_info("for_math_test/data_test")
        print(f"[OK] Found {len(pdf_files)} PDF files in data_test folder:")
        for pdf in pdf_files:
            print(f"   - {pdf['name']} ({pdf['size']} bytes)")
    else:
        print("[ERROR] data_test folder not found")
        return

    # Setup Gemini API
    if setup_gemini():
        print("[OK] Gemini API configured")
    else:
        print("[WARNING] Gemini API not configured (some features may not work)")

    # Check image extraction support
    if PDF_IMAGE_SUPPORT:
        print("[OK] PDF image extraction libraries available")
    else:
        print("[WARNING] PDF image extraction libraries not available")

    print()

    # Step 2: Generate Multiple Exercises
    print(f"STEP 2: Multiple Exercises Generation ({num_exercises} exercises)")
    print("-" * 40)

    try:
        questions, correct_answers, exercise_image_map, all_images = generate_interview_content(num_exercises)

        if questions and len(questions) == num_exercises:
            print(f"[OK] Generated {len(questions)} exercises from PDF:")
            for i, exercise in enumerate(questions, 1):
                print(f"\n{'='*60}")
                print(f"EXERCISE {i}")
                print(f"{'='*60}")
                # Clean Unicode characters before printing
                clean_exercise = exercise.replace('\u200b', '').replace('\ufeff', '').replace('\u2705', '').replace('\u2713', '')
                # Remove other common Unicode symbols that might cause issues
                import re
                clean_exercise = re.sub(r'[^\x00-\x7F]+', '', clean_exercise)
                print(f"{clean_exercise}")

                # Display images specific to this exercise
                exercise_images = exercise_image_map.get(exercise, [])
                if exercise_images:
                    print(f"\n{'-' * 60}")
                    print(f"IMAGES ASSOCIEES A L'EXERCICE {i} ({len(exercise_images)} images)")
                    print(f"{'-' * 60}")
                    for j, img in enumerate(exercise_images, 1):
                        print(f"Image {j} ------------------------------")
                        print(f"Format: {img['extension'].upper()}")
                        print(f"Page: {img['page']}")
                        if img.get('is_virtual'):
                            print(f"Type: URL externe")
                            print(f"URL: {img.get('url', 'N/A')[:50]}...")
                        else:
                            print(f"Type: Image PDF integree")
                        print(f"Reference: Liee a l'exercice {i}")
                        print(f"-----------------------------------------")

                        # Display the image (works for both URL and base64 images)
                        display_image_in_terminal(img['data_url'])
                        print()
                else:
                    print(f"\n[INFO] Aucune image specifique pour l'Exercice {i}")

                if exercise in correct_answers:
                    print(f"\n[HINT] Correct Answer Preview: {correct_answers[exercise][:150]}...")
                print(f"{'='*60}")

            # Summary of all images
            if all_images:
                print(f"\n{'=' * 60}")
                print(f"RESUME DES IMAGES - PDF Complet")
                print(f"{'=' * 60}")
                print(f"Total d'images dans le PDF: {len(all_images)}")
                print(f"Images par page:")
                page_counts = {}
                for img in all_images:
                    page = img['page']
                    page_counts[page] = page_counts.get(page, 0) + 1

                for page, count in sorted(page_counts.items()):
                    print(f"   - Page {page}: {count} image(s)")
                print(f"{'=' * 60}")
            else:
                print(f"\n{'-' * 60}")
                print("INFO: Aucune image trouvee dans le PDF")
                print(f"{'-' * 60}")
        else:
            print(f"[ERROR] Failed to generate {num_exercises} exercises")
            return

    except Exception as e:
        print(f"[ERROR] Error generating exercises: {e}")
        return

    print()

    # Step 3: ANSWER INPUT - TYPE YOUR ANSWERS HERE
    print("\n" + "="*80)
    print("🎯 ANSWER INPUT SECTION - TYPE YOUR ANSWERS BELOW")
    print("="*80)

    user_answers = {}
    for i, exercise in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"📝 EXERCISE {i} - WRITE YOUR ANSWER HERE")
        print(f"{'='*60}")

        # Display exercise text (cleaned)
        clean_exercise = exercise.replace('\u200b', '').replace('\ufeff', '').replace('\u2705', '').replace('\u2713', '')
        import re
        clean_exercise = re.sub(r'[^\x00-\x7F]+', '', clean_exercise)
        print(f"Exercise: {clean_exercise}")

        print(f"\n{'-'*60}")
        print(f"⌨️  TYPE YOUR PYTHON CODE ANSWER FOR EXERCISE {i} BELOW:")
        print(f"{'-'*60}")

        # USER INPUT AREA - THIS IS WHERE YOU TYPE YOUR ANSWER
        print(">>> PASTE OR TYPE YOUR PYTHON CODE HERE <<<")
        user_answer = input().strip()

        if not user_answer:
            user_answer = "# No answer provided"
            print("⚠️  No answer entered")

        user_answers[exercise] = user_answer
        print(f"✅ Answer saved for Exercise {i}")

    print(f"\n{'='*80}")
    print("🎉 ALL ANSWERS COLLECTED! READY FOR EVALUATION")
    print(f"{'='*80}")

    print(f"[OK] Candidate provided answers for {len(user_answers)} exercises:")
    for i, (question, answer) in enumerate(user_answers.items(), 1):
        print(f"\nEXERCISE {i} ANSWER:")
        print(f"   {answer[:300]}{'...' if len(answer) > 300 else ''}")
        print("-" * 50)

    print()

    # Step 4: Evaluate Answer
    print("STEP 4: Answer Evaluation")
    print("-" * 40)

    try:
        print("Evaluating answer...")
        evaluation_results = evaluate_answers(user_answers, correct_answers)

        print("[OK] Evaluation completed!")
        print("\nEVALUATION RESULTS:")
        print("-" * 20)

        total_score = 0
        for i, (question, result) in enumerate(evaluation_results.items(), 1):
            score = result.get('score', 0)
            total_score += score
            justification = result.get('justification', 'No justification provided')

            print(f"\nExercise {i} Score: {score:.2f}/10")
            print(f"   Justification: {justification}")
            print("-" * 30)

        average_score = total_score / len(questions) if questions else 0
        print(f"\nFINAL RESULT:")
        print(f"   Score: {average_score:.2f}/10")
        print(f"   Total Exercises: {len(questions)}")

        # Performance assessment
        if average_score >= 8.0:
            print("   EXCELLENT: Outstanding performance!")
        elif average_score >= 6.0:
            print("   GOOD: Solid performance with room for improvement")
        elif average_score >= 4.0:
            print("   FAIR: Basic understanding, needs more practice")
        else:
            print("   NEEDS IMPROVEMENT: Focus on fundamentals")

    except Exception as e:
        print(f"[ERROR] Error evaluating answer: {e}")
        return

    print()

    # Step 5: Summary
    print("STEP 5: Test Summary")
    print("-" * 40)

    end_time = time.time()
    duration = end_time - start_time

    print("Test Duration: {:.2f} seconds".format(duration))
    print("Exercises Generated: {}".format(len(questions)))
    print("Images Extracted: {}".format(len(all_images) if 'all_images' in locals() else 0))
    print("Answers Evaluated: {}".format(len(evaluation_results)))
    print("Final Score: {:.2f}/10".format(average_score))
    print("Knowledge Base: {} PDF files".format(len(pdf_files)))

    print()
    print("=" * 80)
    print(f"MULTIPLE EXERCISES TEST COMPLETED SUCCESSFULLY! ({num_exercises} EXERCISES)")
    print("=" * 80)

def main():
    """Main function to run the test"""
    print("Starting Recruitment System Test Process...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Number of exercises to generate
    num_exercises = 2

    try:
        run_complete_test_process(num_exercises)
    except KeyboardInterrupt:
        print("\n[WARNING] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nTest process finished")

if __name__ == "__main__":
    main()