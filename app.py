import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PyPDF2 import PdfReader
import docx2txt
import pandas as pd
import os
import re
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Predefined skill list
SKILL_LIST = [
    "python", "java", "machine learning", "data analysis", "communication",
    "teamwork", "sql", "project management", "nlp", "deep learning"
]

# SQLAlchemy setup
Base = declarative_base()

class ResumeRecord(Base):
    __tablename__ = 'resumes'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    jd_text = Column(Text)
    resume_text = Column(Text)
    matched_skills = Column(Text)
    score = Column(Float)

# Use PostgreSQL from environment or fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///resumes.db")
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Helper functions
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def extract_text_from_docx(file):
    return docx2txt.process(file)

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text

def extract_skills(text):
    found_skills = [skill for skill in SKILL_LIST if skill in text]
    return found_skills

def calculate_similarity(jd_text, resumes_text):
    texts = [jd_text] + resumes_text
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(texts)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    return cosine_sim[0]

# Streamlit UI
st.title("📄 Resume Ranking Application with PostgreSQL")

jd_file = st.file_uploader("Upload Job Description", type=["pdf", "docx", "txt"])
resume_files = st.file_uploader("Upload Resumes (Multiple Allowed)", type=["pdf", "docx", "txt"], accept_multiple_files=True)

if jd_file and resume_files:
    # Extract JD text
    if jd_file.type == "application/pdf":
        jd_text = extract_text_from_pdf(jd_file)
    elif jd_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        jd_text = extract_text_from_docx(jd_file)
    else:
        jd_text = jd_file.read().decode("utf-8")

    jd_text = preprocess_text(jd_text)
    jd_skills = extract_skills(jd_text)

    # Extract resumes text
    resumes_text = []
    resume_names = []
    resume_skills = []

    for file in resume_files:
        if file.type == "application/pdf":
            text = extract_text_from_pdf(file)
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file)
        else:
            text = file.read().decode("utf-8")

        clean_text = preprocess_text(text)
        resumes_text.append(clean_text)
        resume_names.append(file.name)
        resume_skills.append(extract_skills(clean_text))

    # Compute similarity scores
    scores = calculate_similarity(jd_text, resumes_text)

    # Rank resumes and store in DB
    session = Session()
    ranked_data = []

    for name, score, skills, text in zip(resume_names, scores, resume_skills, resumes_text):
        matched = list(set(jd_skills) & set(skills))
        skill_score = len(matched) / len(jd_skills) if jd_skills else 0
        final_score = (0.7 * score) + (0.3 * skill_score)
        ranked_data.append((name, score, skill_score, final_score, matched))

        # Save to DB
        record = ResumeRecord(
            name=name,
            jd_text=jd_text,
            resume_text=text,
            matched_skills=','.join(matched),
            score=final_score
        )
        session.add(record)
    session.commit()

    ranked_data.sort(key=lambda x: x[3], reverse=True)

    # Display results
    st.subheader("📊 Ranked Resumes")
    result_df = pd.DataFrame(ranked_data, columns=[
        "Resume", "Text Match Score", "Skill Match Score", "Final Score", "Matched Skills"
    ])
    st.dataframe(result_df)

    # Download CSV
    csv = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv,
        file_name="ranked_resumes.csv",
        mime="text/csv",
    )

# Optional: View saved results from DB
with st.expander("📚 View Saved Results from Database"):
    session = Session()
    saved = session.query(ResumeRecord).order_by(ResumeRecord.score.desc()).all()
    for row in saved:
        st.write(f"{row.name} - Score: {row.score:.2f} - Skills: {row.matched_skills}")
