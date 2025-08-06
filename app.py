import os
import streamlit as st
import pdfplumber
from dotenv import load_dotenv
from langchain_community.llms import Together
from langchain.prompts import PromptTemplate
from tenacity import retry, wait_exponential, stop_after_attempt

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

# Add retry mechanism separately
@retry(wait=wait_exponential(multiplier=1, min=4, max=10), 
       stop=stop_after_attempt(3),
       reraise=True)
def safe_llm_call(prompt):
    try:
        return llm(prompt)
    except Exception as e:
        if "rate limit" in str(e).lower():
            raise  # Will trigger retry
        raise  # Other errors will propagate

# Enhanced error handler
def handle_llm_error(e):
    error_msg = str(e)
    if "rate limit" in error_msg.lower():
        return "⚠️ Our systems are busy (rate limit reached). Please wait 1 minute and try again."
    elif "invalid payload" in error_msg.lower():
        return "🔧 Temporary model issue. Try a different job title or description."
    else:
        return "❌ Service unavailable. Please try again later."

# Helper function to parse JSON from LLM response
def parse_json_response(response):
    """Extract and parse JSON from LLM response, handling extra content"""
    import json
    
    # Clean the response to extract JSON
    response_clean = response.strip()
    
    # Remove markdown code blocks
    if response_clean.startswith('```json'):
        response_clean = response_clean[7:]
    if response_clean.startswith('```'):
        response_clean = response_clean[3:]
    if response_clean.endswith('```'):
        response_clean = response_clean[:-3]
    
    # Find JSON boundaries - look for the first { and last }
    start_idx = response_clean.find('{')
    if start_idx != -1:
        # Find the matching closing brace by counting braces
        brace_count = 0
        end_idx = -1
        for i in range(start_idx, len(response_clean)):
            if response_clean[i] == '{':
                brace_count += 1
            elif response_clean[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        if end_idx != -1:
            response_clean = response_clean[start_idx:end_idx]
    
    response_clean = response_clean.strip()
    
    # Parse JSON
    return json.loads(response_clean)

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
7. Provide ONLY the top 10 most important suggestions

RETURN ONLY VALID JSON IN THIS EXACT FORMAT (no additional text or explanations):
{{
  "analysis": {{
    "target_role": "{job_title}",
    "overall_score": "[Score out of 100]",
    "key_strengths": [
      "Strength 1 based on actual resume content",
      "Strength 2 based on actual resume content",
      "Strength 3 based on actual resume content"
    ],
    "critical_improvements": [
      {{
        "priority": 1,
        "category": "[Skills/Experience/Education/Format]",
        "issue": "Specific issue found in resume",
        "suggestion": "Specific actionable improvement",
        "impact": "How this helps for the target role"
      }},
      {{
        "priority": 2,
        "category": "[Skills/Experience/Education/Format]",
        "issue": "Specific issue found in resume",
        "suggestion": "Specific actionable improvement", 
        "impact": "How this helps for the target role"
      }}
    ],
    "missing_keywords": [
      "keyword1 relevant to {job_title}",
      "keyword2 relevant to {job_title}",
      "keyword3 relevant to {job_title}"
    ],
    "formatting_suggestions": [
      "Specific formatting improvement 1",
      "Specific formatting improvement 2"
    ]
  }}
}}"""
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
        response = safe_llm_call(prompt)
        
        if response:
            # Parse JSON response
            try:
                parsed_response = parse_json_response(response)
                
                # Validate required fields
                if 'analysis' in parsed_response:
                    return parsed_response
                else:
                    st.error("Invalid response format from AI. Missing analysis field.")
                    return None
                    
            except Exception as e:
                st.error(f"Failed to parse AI response as JSON: {str(e)}")
                # Fallback: return raw response in expected format
                return {
                    "analysis": {
                        "target_role": job_title,
                        "overall_score": "Unable to parse",
                        "raw_response": response
                    }
                }
        
        return None
    except Exception as e:
        st.error(handle_llm_error(e))
        return None

def generate_cover_letter(resume_text, job_title, job_description):
    try:
        prompt = COVER_LETTER_PROMPT.format(
            resume_text=resume_text,
            job_title=job_title,
            job_description=job_description
        )
        response = safe_llm_call(prompt)
        
        if response:
            # Parse JSON response
            try:
                parsed_response = parse_json_response(response)
                
                # Validate required fields
                if 'cover_letter' in parsed_response and 'company' in parsed_response:
                    return parsed_response
                else:
                    st.error("Invalid response format from AI. Missing required fields.")
                    return None
                    
            except Exception as e:
                st.error(f"Failed to parse AI response as JSON: {str(e)}")
                # Fallback: return raw response in expected format
                return {
                    "cover_letter": response,
                    "company": "Target Company"
                }
        
        return None
    except Exception as e:
        st.error(handle_llm_error(e))
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
                        st.session_state.analysis_results = analysis
                        st.success("Analysis complete!")
        else:
            help_text = "Please " + " and ".join(missing_items) + " to enable analysis"
            st.button("Analyze Resume", 
                     disabled=True, 
                     help=help_text,
                     on_click=lambda: st.warning(help_text))

        # Display analysis results if available
        if st.session_state.get('analysis_results'):
            # Handle both old string format and new JSON format for backward compatibility
            if isinstance(st.session_state.analysis_results, dict) and 'analysis' in st.session_state.analysis_results:
                analysis_data = st.session_state.analysis_results['analysis']
                
                with st.expander(f"Resume Analysis for {analysis_data.get('target_role', 'Target Role')}"):
                    # Overall Score
                    if 'overall_score' in analysis_data:
                        st.metric("Overall Resume Score", analysis_data['overall_score'])
                    
                    # Key Strengths
                    if 'key_strengths' in analysis_data and analysis_data['key_strengths']:
                        st.subheader("🎯 Key Strengths")
                        for strength in analysis_data['key_strengths']:
                            st.write(f"• {strength}")
                    
                    # Critical Improvements
                    if 'critical_improvements' in analysis_data and analysis_data['critical_improvements']:
                        st.subheader("🔧 Priority Improvements")
                        for improvement in analysis_data['critical_improvements']:
                            with st.container():
                                st.write(f"**Priority {improvement.get('priority', 'N/A')} - {improvement.get('category', 'General')}**")
                                st.write(f"Issue: {improvement.get('issue', 'N/A')}")
                                st.write(f"Suggestion: {improvement.get('suggestion', 'N/A')}")
                                st.write(f"Impact: {improvement.get('impact', 'N/A')}")
                                st.divider()
                    
                    # Missing Keywords
                    if 'missing_keywords' in analysis_data and analysis_data['missing_keywords']:
                        st.subheader("🔍 Missing Keywords")
                        keywords_text = ", ".join(analysis_data['missing_keywords'])
                        st.write(keywords_text)
                    
                    # Formatting Suggestions
                    if 'formatting_suggestions' in analysis_data and analysis_data['formatting_suggestions']:
                        st.subheader("📝 Formatting Improvements")
                        for suggestion in analysis_data['formatting_suggestions']:
                            st.write(f"• {suggestion}")
                            
            else:
                # Fallback for old string format or raw response
                with st.expander("Resume Improvement Suggestions"):
                    if isinstance(st.session_state.analysis_results, dict):
                        if 'suggestions' in st.session_state.analysis_results:
                            st.markdown(st.session_state.analysis_results["suggestions"])
                        elif 'raw_response' in st.session_state.analysis_results.get('analysis', {}):
                            st.markdown(st.session_state.analysis_results['analysis']['raw_response'])
                    else:
                        st.markdown(str(st.session_state.analysis_results))

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
                # Handle both old string format and new JSON format for backward compatibility
                if isinstance(st.session_state.cover_letter, dict):
                    cover_letter_text = st.session_state.cover_letter.get('cover_letter', '')
                    company_name = st.session_state.cover_letter.get('company', 'Target Company')
                else:
                    # Fallback for old string format
                    cover_letter_text = st.session_state.cover_letter
                    company_name = 'Target Company'
                
                with st.expander(f"View Cover Letter for {company_name}"):
                    st.markdown(cover_letter_text)
                
                from docx import Document
                import io
                
                # Create Word document
                doc = Document()
                doc.add_paragraph(cover_letter_text)
                
                # Save to bytes buffer
                doc_bytes = io.BytesIO()
                doc.save(doc_bytes)
                doc_bytes.seek(0)
                
                # Download button
                st.download_button(
                    label="Download Cover Letter as Word",
                    data=doc_bytes,
                    file_name=f"cover_letter_{company_name.replace(' ', '_').lower()}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        elif st.button("Generate Cover Letter", disabled=True):
            st.warning("Please complete all previous steps first")

if __name__ == "__main__":
    main()
