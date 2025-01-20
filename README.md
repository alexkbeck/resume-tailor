# Resume Tailor

A tool that uses AI to tailor your resume for specific job postings while maintaining formatting.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/resume-tailor.git
   cd resume-tailor
   ```

2. Set up Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Google Docs API
   - Configure OAuth consent screen
   - Create OAuth 2.0 credentials
   - Download credentials and save as `credentials.json` in project root

3. Set up environment:
   ```bash
   # Create and activate virtual environment (optional but recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Copy example env file and edit with your values
   cp .env.example .env
   ```

4. Configure `.env` file:
   - Add your OpenAI API key

## Required Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key

## Security Notes

- Never commit `.env`, `credentials.json`, or `token.pickle` to version control
- Keep your API keys and credentials secure
- Add test users to Google Cloud Console for API access
- Ensure your Google Cloud Project is in testing mode with authorized test users

## Usage

1. Prepare your base resume:
   - Create a Google Doc containing your base resume
   - Format it exactly as you want
   - Click 'Share' and copy the link

2. Prepare job posting:
   - Save the job posting text to a file (e.g., `job_posting.txt`)
   - Ensure the file is saved with UTF-8 encoding

3. Run the application:
   ```bash
   python main.py
   ```

4. Follow the prompts:
   - Paste your Google Doc link when prompted
   - Provide the path to your job posting file
   - The tailored resume will be saved as a new Google Doc

## Contributing

1. Fork the repository
2. Create a new branch for your feature: `git checkout -b feature-name`
3. Make your changes
4. Run any tests (when implemented)
5. Commit your changes: `git commit -m 'Add some feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Include docstrings for all functions and classes
- Add comments for complex logic
- Keep functions focused and single-purpose
- Use meaningful variable names

### Project Structure

```
resume_tailor/
├── main.py          # Main application logic
├── .env            # Environment variables (not in repo)
├── .env.example    # Example environment variables
├── requirements.txt # Project dependencies
└── README.md       # Project documentation
```

### Future Improvements

- Add unit tests
- Add logging
- Add CLI arguments for different modes
- Add support for different file formats
- Add support for different job board formats