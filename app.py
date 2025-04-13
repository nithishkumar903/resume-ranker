import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import sql
from streamlit_extras.stylable_container import stylable_container
import time

# Page Configuration
st.set_page_config(page_title="AI Resume Ranker", page_icon="🤖", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    body {
        background-color: #0f172a;
        color: #f1f5f9;
        font-family: 'Segoe UI', sans-serif;
    }
    .main {
        background-color: #1e293b;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
    }
    .title {
        font-size: 3rem;
        font-weight: bold;
        color: #38bdf8;
    }
    .subtitle {
        font-size: 1.3rem;
        color: #cbd5e1;
    }
    .stButton>button {
        background-color: #0ea5e9;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 20px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0284c7;
    }
    .stTextInput>div>input, .stTextArea>div>textarea {
        border-radius: 10px;
        background-color: #f8fafc;
        color: black;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main'>", unsafe_allow_html=True)

# Header
st.markdown("<div class='title'>AI Resume Ranking System 🚀</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Upload a resume and we'll rank it based on your job criteria.</div><br>", unsafe_allow_html=True)

# Database Connection (PostgreSQL)
def connect_db():
    return psycopg2.connect(
        host="localhost",
        database="resume_ranker",
        user="postgres",
        password="your_password",
        port=5432
    )

# Stylish Login Section
with stylable_container(
    key="login",
    css_styles="""
        padding: 10px;
        margin-bottom: 20px;
        background-color: #1e293b;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    """
):
    st.subheader("🔐 Login to access dashboard")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.success("Logged in successfully!")
        else:
            st.error("Invalid credentials.")

# Upload Resume
uploaded_file = st.file_uploader("📄 Upload Resume (PDF or TXT only)", type=["pdf", "txt"])

# Job Keywords Input
keywords = st.text_input("💼 Enter Job Keywords (comma-separated)", placeholder="e.g. Python, NLP, Machine Learning")

# Process Button
if st.button("🔍 Rank Resume"):
    if uploaded_file is not None and keywords:
        with st.spinner("Processing resume..."):
            time.sleep(2)
            resume_text = uploaded_file.read().decode("utf-8", errors='ignore')
            keyword_list = [kw.strip().lower() for kw in keywords.split(",")]
            match_count = sum(1 for kw in keyword_list if kw in resume_text.lower())
            score = (match_count / len(keyword_list)) * 100

        st.subheader("📊 Resume Score")
        st.progress(int(score))
        st.metric("Match %", f"{score:.2f}%")

        try:
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO resume_scores (filename, keywords, score)
                VALUES (%s, %s, %s)
            """, (uploaded_file.name, keywords, score))
            conn.commit()
            conn.close()
            st.success("✅ Resume saved to database.")
        except Exception as e:
            st.error(f"Database error: {e}")
    else:
        st.warning("⚠️ Please upload a resume and enter keywords.")

# Dashboard View
with st.expander("📈 Show All Resume Scores"):
    try:
        conn = connect_db()
        df = pd.read_sql_query("SELECT * FROM resume_scores ORDER BY id DESC", conn)
        st.dataframe(df, use_container_width=True)
        conn.close()
    except Exception as e:
        st.error(f"Couldn't load dashboard: {e}")

st.markdown("""
---
👨‍💻 Built with ❤️ by your AI team | Dark Mode Enabled 🌙
""")

st.markdown("</div>", unsafe_allow_html=True)
