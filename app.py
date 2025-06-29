import os
import streamlit as st
import pdfplumber
from dotenv import load_dotenv
from langchain_community.llms import Together
from langchain.prompts import PromptTemplate

# App configuration
st.set_page_config(
    page_title="Resume Analyzer & Cover Letter Generator",
    page_icon="📄",
    layout="wide"
)

# Modern dark theme
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    .css-1aumxhk {
        background-color: #1E1E1E;
    }
</style>
""", unsafe_allow_html=True)

# Load environment variables
try:
    # First try Streamlit secrets (for cloud deployment)
    TOGETHER_API_KEY = st.secrets['TOGETHER_API_KEY']
except Exception:
    # Fallback to .env for local development
    load_dotenv()
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
    if not TOGETHER_API_KEY:
        st.error("API key not configured. Please set TOGETHER_API_KEY in secrets or .env file")
        st.stop()

# Initialize Together AI client
llm = Together(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    temperature=0.3,
    max_tokens=2000,
    together_api_key=TOGETHER_API_KEY
)

# Prompt templates
RESUME_ANALYSIS_PROMPT = PromptTemplate(
    input_variables=["job_title", "resume_text"],
    template="""Analyze THIS resume for THIS job title and provide SPECIFIC improvements:

RESUME CONTENT:
{resume_text}

TARGET ROLE: {job_title}

STRICT RULES:
1. EVERY suggestion must reference ACTUAL resume content
2. NO generic advice - only what's missing/needs improvement
3. For skills: Only suggest adding what's in job title/description
4. For experience: Only suggest quantifying ACTUAL resume items
5. Reject any suggestion not directly tied to this resume
6. Rank all suggestions by importance (1 = most critical)
7. Provide ONLY the top 10 most important suggestions"""
)

COVER_LETTER_PROMPT = PromptTemplate(
    input_variables=["resume_text", "job_title", "job_description"],
    template="""Create a HIGHLY TARGETED cover letter using ONLY the most relevant details:

RESUME CONTENT:
{resume_text}

JOB REQUIREMENTS:
{job_description}

STRICT RULES:
1. Only include skills/projects/certifications that DIRECTLY MATCH the job requirements
2. For technical roles (like generative AI), ONLY include relevant technical items
3. Every claim must be PROVEN by resume content
4. Structure content to show HOW your experience solves company's needs
5. Reject any content not directly applicable to this specific role

FORMAT:
[Date]

[Company Info]

Dear [Hiring Manager],

[Paragraph 1: Most relevant experience matching exact role needs]
[Paragraph 2: Technical skills that directly address job requirements]
[Paragraph 3: Quantified achievements solving similar challenges]

Sincerely,
[Your Name]
[Your Contact Info]"""
)

# Initialize session state
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'job_title' not in st.session_state:
    st.session_state.job_title = ""
if 'job_description' not in st.session_state:
    st.session_state.job_description = ""
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'cover_letter' not in st.session_state:
    st.session_state.cover_letter = ""

# Analysis functions
def analyze_resume(job_title, resume_text):
    try:
        prompt = RESUME_ANALYSIS_PROMPT.format(
            job_title=job_title,
            resume_text=resume_text
        )
        return llm(prompt)
    except Exception as e:
        if "rate limit" in str(e).lower():
            st.warning("Our systems are currently busy. Please wait a minute and try again.")
        else:
            st.error(f"Analysis failed: Please try again later")
        return None

def generate_cover_letter(resume_text, job_title, job_description):
    try:
        prompt = COVER_LETTER_PROMPT.format(
            resume_text=resume_text,
            job_title=job_title,
            job_description=job_description
        )
        return llm(prompt)
    except Exception as e:
        if "rate limit" in str(e).lower():
            st.warning("Our systems are currently busy. Please wait a few minutes and try again.")
        else:
            st.error(f"Cover letter generation failed: Please try again later")
        return None

# Main app function
def main():
    # Resume upload section
    with st.container():
        st.header("Step 1: Upload Your Resume")
        uploaded_file = st.file_uploader(
            "Choose a PDF file (max 10MB)", 
            type="pdf", 
            accept_multiple_files=False,
            help="For optimal performance, please keep files under 10MB"
        )

        if uploaded_file is not None:
            if uploaded_file.size > 10 * 1024 * 1024:  # 10MB in bytes
                st.error("File size exceeds 10MB limit. Please upload a smaller file.")
            else:
                try:
                    with pdfplumber.open(uploaded_file) as pdf:
                        text = "\n".join([page.extract_text() for page in pdf.pages])
                    st.session_state.resume_text = text
                    st.success("Resume successfully uploaded and parsed!")
                    with st.expander("View extracted resume text"):
                        st.text(text)
                except Exception as e:
                    st.error(f"Error processing PDF: {str(e)}")

    # Job title and analysis section
    with st.container():
        st.header("Step 2: Enter Job Title")
        job_title = st.text_input(
            "Target job title",
            value=st.session_state.get("job_title", ""),
            placeholder="e.g. Senior Software Engineer",
            help="Enter the job title you're applying for",
            key="job_title_input",
            on_change=lambda: st.session_state.update({"job_title": st.session_state.job_title_input})
        )

        if st.session_state.get('job_title'):
            st.success(f"Analyzing resume for: {st.session_state.job_title}")

        # Analysis button with enhanced hover help
        missing_items = []
        if not st.session_state.get('resume_text'):
            missing_items.append("upload a resume")
        if not st.session_state.get('job_title'):
            missing_items.append("enter a job title")
            
        if not missing_items:
            if st.button("Analyze Resume", type="primary"):
                with st.spinner('Analyzing your resume...'):
                    analysis = analyze_resume(
                        st.session_state.job_title,
                        st.session_state.resume_text
                    )
                    if analysis:
                        st.session_state.analysis_results = {"suggestions": analysis}
                        st.success("Analysis complete!")
        else:
            help_text = "Please " + " and ".join(missing_items) + " to enable analysis"
            st.button("Analyze Resume", 
                     disabled=True, 
                     help=help_text,
                     on_click=lambda: st.warning(help_text))

        # Display analysis results if available
        if st.session_state.get('analysis_results'):
            with st.expander("Resume Improvement Suggestions"):
                st.markdown(st.session_state.analysis_results["suggestions"])

    # Job description section
    with st.container():
        st.header("Step 3: Enter Job Description")
        job_desc = st.text_area(
            "Paste the job description",
            value=st.session_state.get("job_description", ""),
            placeholder="Paste the full job description here...",
            help="This helps generate a targeted cover letter",
            key="job_desc_input",
            on_change=lambda: st.session_state.update({"job_description": st.session_state.job_desc_input})
        )

        if st.session_state.resume_text and st.session_state.job_title and st.session_state.job_description:
            if st.button("Generate Cover Letter", type="primary"):
                with st.spinner('Generating your cover letter...'):
                    cover_letter = generate_cover_letter(
                        st.session_state.resume_text,
                        st.session_state.job_title,
                        st.session_state.job_description
                    )
                    if cover_letter:
                        st.session_state.cover_letter = cover_letter
                        st.success("Cover letter generated!")

            # Display cover letter if available
            if st.session_state.cover_letter:
                with st.expander("View Cover Letter"):
                    st.markdown(st.session_state.cover_letter)
                from docx import Document
                import io
                
                # Create Word document
                doc = Document()
                doc.add_paragraph(st.session_state.cover_letter)
                
                # Save to bytes buffer
                doc_bytes = io.BytesIO()
                doc.save(doc_bytes)
                doc_bytes.seek(0)
                
                # Download button
                st.download_button(
                    label="Download Cover Letter as Word",
                    data=doc_bytes,
                    file_name="generated_cover_letter.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        elif st.button("Generate Cover Letter", disabled=True):
            st.warning("Please complete all previous steps first")

if __name__ == "__main__":
    main()
