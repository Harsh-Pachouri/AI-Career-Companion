# AI-Powered Resume Analyzer & Cover Letter Generator

A Streamlit application that analyzes resumes and generates targeted cover letters using LangChain and Together AI.

## Features
- Resume analysis with specific improvement suggestions
- AI-generated, role-specific cover letters
- Secure API key management

## Setup
1. Clone the repository
2. Create `.env` file for local development:
   ```
   TOGETHER_API_KEY=your_api_key_here
   ```
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Deployment
For Streamlit Community Cloud:
1. Add your `TOGETHER_API_KEY` in the Secrets manager
2. Deploy from GitHub
