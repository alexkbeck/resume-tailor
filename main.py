"""Resume tailoring application using OpenAI API and Google Docs."""

from openai import OpenAI
import os
import re
import pickle
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
from typing import Tuple, List, Dict, Any
import logging

# Load environment variables
load_dotenv()

# Google Docs API setup
SCOPES = ['https://www.googleapis.com/auth/documents']

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MODEL_NAME = "gpt-4o-mini"
SUPPORTED_ENCODINGS = ['utf-8', 'utf-16', 'ascii', 'iso-8859-1', 'cp1252']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ResumeError(Exception):
    """Base exception class for resume tailor errors."""
    pass

class FileReadError(ResumeError):
    """Raised when there's an error reading a file."""
    pass

class APIError(ResumeError):
    """Raised when there's an error with API calls."""
    pass

def check_environment():
    """Check if all required environment variables are set.

    Raises:
        ValueError: If any required environment variable is missing.
    """
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError("OPENAI_API_KEY not found in environment variables")


def extract_doc_id(doc_link):
    """Extract Google Doc ID from a sharing link.
    
    Args:
        doc_link (str): The Google Doc sharing link.
        
    Returns:
        str: The extracted document ID.
        
    Raises:
        ValueError: If the link format is invalid.
    """
    pattern = r'/document/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, doc_link)
    if not match:
        raise ValueError("Invalid Google Doc link format")
    return match.group(1)


def get_google_auth():
    """Initialize and return Google authentication credentials.
    
    Returns:
        Credentials: The authenticated Google credentials.
    """
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def read_doc(service: Resource, doc_id: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Read and return the content and styling of a Google Doc.
    
    Args:
        service: The Google Docs service instance.
        doc_id: The ID of the document to read.
        
    Returns:
        A tuple containing:
            - The document's text content
            - A list of style dictionaries, each containing:
                - start_index: Starting position of the style
                - end_index: Ending position of the style
                - style: Dictionary of style attributes
        
    Raises:
        Exception: If the document cannot be accessed or read.
    """
    try:
        document = service.documents().get(documentId=doc_id).execute()
        doc_content = document.get('body', {}).get('content', [])
        text = ''
        styles = []
        current_index = 0
        
        for element in doc_content:
            if 'paragraph' in element:
                for para_element in element['paragraph']['elements']:
                    if 'textRun' in para_element:
                        text_run = para_element['textRun']
                        content = text_run['content']
                        if text_run.get('textStyle'):
                            styles.append({
                                'start_index': current_index,
                                'end_index': current_index + len(content),
                                'style': text_run['textStyle']
                            })
                        text += content
                        current_index += len(content)
        
        return text.strip(), styles
    except Exception as e:
        raise Exception(f"Failed to read document: {str(e)}")


def get_base_resume():
    """Prompt user for a base resume and validate the link.
    
    Returns:
        str: The ID of the base resume document.

    Raises:
        ValueError: If the link format is invalid.
    """
    print("\nPlease share your resume.")
    print("1. Open your resume in Google Docs")
    print("2. Click 'Share' and copy the link")
    print("3. Paste the link below\n")

    while True:
        doc_link = input("Enter Google Doc link: ").strip()
        try:
            doc_id = extract_doc_id(doc_link)
            return doc_id
        except ValueError:
            print("Invalid link format. Please provide a valid Google Doc link.")


def get_job_posting():
    """Prompt user for job posting text from a file.
    
    Returns:
        str: The job posting text.
        
    Raises:
        Exception: If there's an error reading the file.
    """
    print("\nPlease save the job posting in a text file and provide the path.")
    print("Example: ./job_posting.txt\n")
    
    while True:
        try:
            file_path = input("Enter file path: ").strip()
            if file_path.lower() in ['exit', 'quit', 'q']:
                raise KeyboardInterrupt
                
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'ascii', 'iso-8859-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        content = file.read().strip()
                        if not content:
                            print("Error: File is empty. Please provide a file with content.")
                            break
                        return content
                except UnicodeDecodeError:
                    continue  # Try next encoding
                except FileNotFoundError:
                    print(f"Error: File '{file_path}' not found. Please try again or type 'exit' to quit.")
                    break
                except Exception as e:
                    print(f"Error reading file: {e}")
                    print("Please try again or type 'exit' to quit.")
                    break
            else:  # No encoding worked
                print("Error: Unable to read file with supported encodings.")
                print("Please ensure the file is saved with UTF-8 encoding or type 'exit' to quit.")

        except KeyboardInterrupt:
            print("\nExiting application...")
            raise SystemExit(0)


def tailor_resume(client, resume_text, job_text):
    """Generate a tailored version of the resume for the job posting.
    
    Args:
        client: The OpenAI client instance.
        resume_text (str): The original resume content.
        job_text (str): The job posting content.
        
    Returns:
        str: The tailored resume content.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """You are an expert at subtly tailoring resumes to job descriptions.
                    Your task is to:
                    1. Identify key skills and requirements from the job posting
                    2. Modify the resume to emphasize relevant experience and skills
                    3. Use your own phrasing - do not copy text directly from the job posting
                    4. Keep modifications subtle and natural-sounding
                    5. Maintain the exact same formatting as the original resume
                    6. Preserve the overall length and structure
                    
                    Only output the modified resume content, no explanations or other text."""
                },
                {
                    "role": "user", 
                    "content": f"Job Posting:\n\n{job_text}\n\nOriginal Resume:\n\n{resume_text}\n\nProvide the tailored resume:"
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise Exception(f"Failed to tailor resume: {str(e)}")


def extract_job_details(client, job_text):
    """Extract company name and job title from job posting using OpenAI API.
    
    Args:
        client: The OpenAI client instance.
        job_text (str): The job posting content.
        
    Returns:
        tuple: (company_name, job_title)
        
    Raises:
        ValueError: If company name or job title cannot be extracted.
        Exception: If API call fails.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Extract the company name and exact job title from the job posting.
                    Use the official title as written, not a generic version.
                    Respond in the format:
                    Company: <name>
                    Title: <title>"""
                },
                {
                    "role": "user",
                    "content": job_text
                }
            ]
        )
        response = completion.choices[0].message.content
        
        # Parse response
        company = ""
        title = ""
        for line in response.split('\n'):
            if line.startswith('Company:'):
                company = line.replace('Company:', '').strip()
            elif line.startswith('Title:'):
                title = line.replace('Title:', '').strip()
        
        if not company or not title:
            raise ValueError("Failed to extract company name or job title from response")
            
        return company, title
    except Exception as e:
        raise Exception(f"Failed to extract job details: {str(e)}")


def get_base_doc_title(service, doc_id):
    """Get the title of the base resume document.
    
    Args:
        service: The Google Docs service instance.
        doc_id (str): The ID of the document.
        
    Returns:
        str: The document title.
    """
    try:
        document = service.documents().get(documentId=doc_id).execute()
        return document.get('title', 'Resume')
    except Exception as e:
        raise Exception(f"Failed to get document title: {str(e)}")


def create_tailored_resume(service, title, content, styles):
    """Create a new Google Doc with the tailored resume, preserving formatting.
    
    Args:
        service: The Google Docs service instance.
        title (str): The title for the new document.
        content (str): The resume content.
        styles (list): List of text style information.
        
    Returns:
        str: The ID of the created document.
    """
    try:
        # Create new document
        document = service.documents().create(body={'title': title}).execute()
        doc_id = document.get('documentId')
        
        # Insert content
        requests = [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': content
                }
            }
        ]
        
        # Apply text styles
        for style_info in styles:
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': style_info['start_index'] + 1,  # +1 because we inserted at index 1
                        'endIndex': style_info['end_index'] + 1
                    },
                    'textStyle': style_info['style'],
                    'fields': ','.join(style_info['style'].keys())
                }
            })
        
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        return doc_id
    except Exception as e:
        raise Exception(f"Failed to create tailored resume document: {str(e)}")


def main():
    """Main execution function."""
    try:
        # Check environment variables
        check_environment()

        # Get base resume document ID
        doc_id = get_base_resume()

        # Initialize Google Docs service
        creds = get_google_auth()
        docs_service = build('docs', 'v1', credentials=creds)

        # Read content from Google Doc
        logging.info("Reading resume content...")
        resume_content, styles = read_doc(docs_service, doc_id)

        # Get job posting
        print("\nNext, let's get the job posting details.")
        job_content = get_job_posting()

        # Extract job details
        print("\nExtracting job details...")
        company_name, job_title = extract_job_details(client, job_content)
        
        # Get base resume title
        base_title = get_base_doc_title(docs_service, doc_id)
        
        # Generate tailored resume
        print("\nTailoring resume for the position...")
        tailored_content = tailor_resume(client, resume_content, job_content) 
        
        # Create new document
        new_title = f"{base_title} - {company_name} - {job_title}"
        print(f"\nCreating new document: {new_title}")
        new_doc_id = create_tailored_resume(docs_service, new_title, tailored_content, styles)
        
        print(f"\nTailored resume saved to new document. You can find it in your Google Drive.")
        print(f"Document title: {new_title}")

    except Exception as e:
        print(f"\nError: {str(e)}")
        return 1

    return 0


if __name__ == '__main__':
    main()
