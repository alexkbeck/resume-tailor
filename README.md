# Resume Tailor

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your values
3. Place your Google API credentials file as `credentials.json` in the project root
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python main.py`

## Required Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key

## Security Notes

- Never commit `.env`, `credentials.json`, or `token.pickle` to version control
- Keep your API keys and credentials secure
- Add test users to Google Cloud Console for API access

## Usage

1. Create a Google Doc containing your base resume
2. Click the 'Share' button and copy the link
3. Save the job posting in a text file (e.g., job_posting.txt)
4. Run the application: `python main.py`
5. Paste the Google Doc link when prompted
6. Enter the path to your job posting text file

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
├── main.py # Main application logic
├── .env # Environment variables (not in repo)
├── .env.example # Example environment variables
├── requirements.txt # Project dependencies
└── README.md # Project documentation
```

### Future Improvements

- Add unit tests
- Add logging
- Add CLI arguments for different modes
- Add support for different file formats
- Add support for different job board formats