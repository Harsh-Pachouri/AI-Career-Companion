# Resume Analyzer & Cover Letter Generator

An intelligent Streamlit application that analyzes resumes, provides improvement suggestions, and generates personalized cover letters using AI-powered insights.
Features

- Resume Upload & Parsing: Upload PDF resumes and extract text content automatically
Smart Resume Analysis: Get ranked, actionable improvement suggestions tailored to specific job titles
- Cover Letter Generation: Create personalized cover letters based on your resume and job descriptions
- AI-Powered: Utilizes Meta's Llama-3.3-70B model via Together AI for intelligent recommendations
- Secure: Private deployment with encrypted API key management
- Responsive: Works seamlessly on desktop and mobile devices

## Tech Stack

Frontend: Streamlit
PDF Processing: pdfplumber
AI Integration: LangChain + Together AI
Model: meta-llama/Llama-3.3-70B-Instruct-Turbo-Free
Deployment: Streamlit Community Cloud

## Live Demo
Try the App (Replace with your actual deployment URL)
Prerequisites

Python 3.8 or higher
Together AI API key (Get one here)
Git (for deployment)

🔧 Installation
Local Development

Clone the repository
bashgit clone https://github.com/yourusername/resume-analyzer-app.git
cd resume-analyzer-app

Create virtual environment
bashpython -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies
bashpip install -r requirements.txt

Run the application
bashstreamlit run app.py

Open your browser to http://localhost:8501

## Usage Guide
Step 1: Upload Resume

Click "Browse files" or drag & drop your PDF resume
The app will automatically extract and display the text content
Verify the extracted text is accurate

Step 2: Get Resume Improvements

Enter the job title you're targeting (e.g., "Software Engineer", "Marketing Manager")
Click "Analyze Resume" to get 7-10 ranked improvement suggestions
Review suggestions focusing on keywords, metrics, and formatting

Step 3: Generate Cover Letter

Paste the job description from your target job posting
Click "Generate Cover Letter"
Review and customize the generated cover letter
Download or copy the final version

## Example Workflow
- Upload: "John_Doe_Resume.pdf"
- Job Title: "Data Scientist"
- Improvements: 
   1. Add Python and SQL keywords to skills section
   2. Quantify machine learning project impact with metrics
   3. Include data visualization tools experience
   ...

- Job Description: "We're seeking a Data Scientist with 3+ years..."
- Generated Cover Letter: Professional, tailored letter highlighting relevant experience
- Security & Privacy

- Private Repository: Code and configurations remain secure
- API Key Protection: Keys stored in encrypted Streamlit secret
- No Data Storage: Uploaded resumes are processed in memory only
- HTTPS: All communications encrypted in transit

## Project Structure
resume-analyzer-app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore           # Git ignore rules
├── .streamlit/
│   ├── secrets.toml     # API keys (local only - not committed)
│   └── config.toml      # Streamlit configuration
└── utils/
    └── prompts.py       # AI prompt templates
## Contributing

Fork the repository
Create a feature branch: git checkout -b feature/amazing-feature
Commit changes: git commit -m 'Add amazing feature'
Push to branch: git push origin feature/amazing-feature
Open a Pull Request
