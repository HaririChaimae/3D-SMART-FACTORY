#!/usr/bin/env python3
"""
TEST CHAT INTERFACE: Streamlit Interface for Recruitment System Testing
=======================================================================

A simple Streamlit interface to test the complete recruitment system process.
This interface allows you to interact with the test system through a web UI.

Features:
- Generate questions from knowledge base
- Simulate candidate taking test
- Evaluate answers with AI
- View results and performance

Author: Kilo Code
Date: 2025-09-11
"""

import streamlit as st
import sys
import os
import json
import time
import base64
from datetime import datetime
from io import BytesIO

# Add current directory to path
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
import google.generativeai as genai
import re
import logging

# Import all comprehensive functions from test_file_test.py
from test_file_test import (
    setup_gemini,
    get_pdf_files_info,
    extract_images_from_pdf,
    display_image_in_terminal,
    build_vector_store_cached,
    extract_text_with_page_info,
    analyze_link_image_relationships,
    extract_image_urls_from_text,
    associate_images_with_exercises,
    generate_exercises_from_pdf,
    extract_exercises_from_pdf,
    rag_answer_exercise,
    generate_interview_content,
    simulate_candidate_answers,
    run_complete_test_process
)

# Try to import PDF image extraction libraries
try:
    from PyPDF2 import PdfReader
    from PIL import Image
    import fitz  # PyMuPDF for better image extraction
    PDF_IMAGE_SUPPORT = True
except ImportError:
    PDF_IMAGE_SUPPORT = False
    st.warning("PDF image extraction libraries not available. Install PyMuPDF and Pillow for full functionality.")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Recruitment System Test Interface",
    page_icon="🧪",
    layout="wide"
)

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'correct_answers' not in st.session_state:
    st.session_state.correct_answers = {}
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'exercise_image_map' not in st.session_state:
    st.session_state.exercise_image_map = {}







def generate_multiple_exercises_with_images(num_exercises=2, job_matching_result=None):
    """Generate multiple interview exercises with image support using comprehensive functions from test_file_test.py"""
    with st.spinner(f"Generating {num_exercises} exercises with image support..."):
        # Use the comprehensive generate_interview_content function from test_file_test.py
        exercises, correct_answers, exercise_image_map, all_images = generate_interview_content(num_exercises, job_matching_result)

        if exercises:
            st.success(f"Successfully generated {len(exercises)} exercises with comprehensive image support")
            if job_matching_result:
                st.info(f"Questions generated based on job matching: {job_matching_result}")
        else:
            st.warning("Failed to generate exercises, using fallback")

        return exercises, correct_answers, exercise_image_map, all_images

def simulate_candidate_answers(questions):
    """Simulate candidate providing answers using comprehensive function from test_file_test.py"""
    st.info("Simulating candidate answers using comprehensive simulation...")
    # Import and use the comprehensive simulate_candidate_answers function from test_file_test.py
    from test_file_test import simulate_candidate_answers as simulate_from_test
    user_answers = simulate_from_test(questions)
    st.success(f"Generated sample answers for {len(user_answers)} exercises")
    return user_answers



def evaluate_answers_interface(user_answers, correct_answers):
    """Evaluate answers with progress"""
    with st.spinner('Evaluating answers...'):
        try:
            evaluation_results = evaluate_answers(user_answers, correct_answers)
            st.success("Evaluation completed!")
            return evaluation_results
        except Exception as e:
            st.error(f"Error evaluating answers: {e}")
            return {}

def main():
    """Main Streamlit interface"""
    st.title("📝 Mathematics Exercise Interface")
    st.markdown("Generate exercises with images and provide your answers.")

    # Check system status
    col1, col2 = st.columns(2)
    with col1:
        pdf_files = get_pdf_files_info()
        if pdf_files:
            st.success(f"✅ {len(pdf_files)} PDF files found")
        else:
            st.error("❌ No PDF files found")

    with col2:
        if setup_gemini():
            st.success("✅ Gemini API configured")
        else:
            st.warning("⚠️ Gemini API not configured")

    st.markdown("---")

    # Generate exercises section
    if not st.session_state.questions:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            num_exercises = st.selectbox("Number of exercises:", [1, 2, 3, 4, 5], index=1)
        with col2:
            job_matching = st.text_input("Job matching (optional):", placeholder="e.g., Mathematician")
        with col3:
            if st.button("🎯 Generate Exercises", type="primary", use_container_width=True):
                questions, correct_answers, exercise_image_map, all_images = generate_multiple_exercises_with_images(num_exercises, job_matching if job_matching.strip() else None)

                if questions:
                    st.session_state.questions = questions
                    st.session_state.correct_answers = correct_answers
                    st.session_state.exercise_image_map = exercise_image_map
                    st.success(f"✅ Generated {len(questions)} exercises!")
                    st.rerun()
                else:
                    st.error("Failed to generate exercises")
    else:
        # Display exercises with input areas
        st.header("📝 Exercises & Answers")

        for i, question in enumerate(st.session_state.questions, 1):
            st.markdown(f"## 🎯 Exercise {i}")
            st.markdown("---")

            # Display exercise text
            with st.container():
                st.markdown("### 📋 Exercise:")
                # Extract title from first line or use default
                first_line = question.split('\n')[0].strip()
                if first_line.lower().startswith('exercice'):
                    exercise_title = first_line
                else:
                    exercise_title = f"Exercise {i}"
                st.markdown(f"**{exercise_title}**")
                st.info(question)

            # Display images if any
            exercise_images = st.session_state.exercise_image_map.get(question, [])
            if exercise_images:
                st.markdown("### 📸 Related Images:")
                for j, img in enumerate(exercise_images, 1):
                    st.markdown(f"**Image {j}:**")
                    st.markdown(f"""
                    <div style="text-align: center; margin: 10px 0;">
                        <img src="{img['data_url']}" alt="Image {j}" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px;">
                    </div>
                    """, unsafe_allow_html=True)

            # Answer input area
            st.markdown(f"### ⌨️ Your Answer for Exercise {i}:")

            user_answer = st.text_area(
                f"Write your Python code solution for Exercise {i}:",
                value=st.session_state.user_answers.get(question, ""),
                height=300,
                key=f"answer_{i}",
                help=f"Write your complete Python solution for Exercise {i}",
                placeholder=f"# EXERCISE {i} SOLUTION\n# Write your Python code here\n\ndef solution():\n    # Your code here\n    pass\n\n# Test your solution\nif __name__ == '__main__':\n    # Test code here\n    pass"
            )

            # Store answer
            st.session_state.user_answers[question] = user_answer

            if user_answer.strip():
                st.success(f"✅ Answer saved ({len(user_answer)} characters)")
            else:
                st.warning("Please provide an answer")

            st.markdown("---")

        # Submit and evaluate section
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Submit & Evaluate", type="primary", use_container_width=True):
                # Check if all answers provided
                all_answered = all(
                    st.session_state.user_answers.get(q, "").strip()
                    for q in st.session_state.questions
                )

                if all_answered:
                    with st.spinner("Evaluating answers..."):
                        evaluation_results = evaluate_answers_interface(
                            st.session_state.user_answers,
                            st.session_state.correct_answers
                        )

                    st.success("✅ Evaluation completed!")

                    # Display results
                    st.header("📊 Evaluation Results")

                    total_score = 0
                    for i, (question, result) in enumerate(evaluation_results.items(), 1):
                        score = result.get('score', 0)
                        total_score += score
                        justification = result.get('justification', 'No justification provided')

                        with st.expander(f"Exercise {i} - Score: {score:.2f}/10", expanded=True):
                            st.write(f"**Score:** {score:.2f}/10")
                            st.write(f"**Justification:** {justification}")
                            st.progress(score / 10)

                    average_score = total_score / len(st.session_state.questions) if st.session_state.questions else 0

                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Average Score", f"{average_score:.2f}/10")
                    with col2:
                        st.metric("Exercises", len(evaluation_results))
                    with col3:
                        if average_score >= 8.0:
                            st.metric("Performance", "EXCELLENT")
                        elif average_score >= 6.0:
                            st.metric("Performance", "GOOD")
                        elif average_score >= 4.0:
                            st.metric("Performance", "FAIR")
                        else:
                            st.metric("Performance", "NEEDS IMPROVEMENT")
                else:
                    st.error("⚠️ Please provide answers for all exercises")

        with col2:
            if st.button("🔄 New Exercises", use_container_width=True):
                st.session_state.questions = []
                st.session_state.correct_answers = {}
                st.session_state.user_answers = {}
                st.session_state.exercise_image_map = {}
                st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("*Mathematics Exercise Interface - Built with Streamlit*")

if __name__ == "__main__":
    main()