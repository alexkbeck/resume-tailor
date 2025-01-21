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
        
    Raises:
        Exception: If authentication fails.
    """
    def remove_token_and_retry():
        """Remove token.pickle and create new credentials."""
        if os.path.exists('token.pickle'):
            logging.info("Removing expired token...")
            os.remove('token.pickle')
        
        logging.info("Getting new token...")
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        new_creds = flow.run_local_server(port=0)
        
        # Save the new credentials
        with open('token.pickle', 'wb') as token:
            pickle.dump(new_creds, token)
        
        return new_creds

    try:
        creds = None
        
        # Try to load existing credentials
        if os.path.exists('token.pickle'):
            try:
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logging.warning(f"Error reading token.pickle: {str(e)}")
                return remove_token_and_retry()
        
        # If no valid credentials available, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logging.info("Refreshing expired token...")
                    creds.refresh(Request())
                    # Save the refreshed credentials
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    logging.warning(f"Error refreshing token: {str(e)}")
                    return remove_token_and_retry()
            else:
                return remove_token_and_retry()

        return creds

    except Exception as e:
        raise Exception(f"Failed to authenticate with Google: {str(e)}")


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
                        # Always capture the style, even if it's empty
                        style_info = {
                            'start_index': current_index,
                            'end_index': current_index + len(content),
                            'style': text_run.get('textStyle', {})
                        }
                        styles.append(style_info)
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
    """Get job posting text from file.
    
    First tries to read from 'job_posting.txt' in the current directory.
    If not found, prompts user for file path.
    
    Returns:
        str: The job posting text.
        
    Raises:
        FileReadError: If there's an error reading the file.
    """
    def read_file_with_encodings(file_path):
        """Helper function to read file with different encodings."""
        for encoding in SUPPORTED_ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read().strip()
                    if not content:
                        raise FileReadError("File is empty")
                    return content
            except UnicodeDecodeError:
                continue
        raise FileReadError(f"Unable to read file with supported encodings: {file_path}")

    # First try job_posting.txt in current directory
    default_file = 'job_posting.txt'
    if os.path.exists(default_file):
        try:
            logging.info(f"Found {default_file}, attempting to read...")
            return read_file_with_encodings(default_file)
        except Exception as e:
            logging.warning(f"Error reading {default_file}: {str(e)}")
            # Fall through to manual input
    
    # If default file not found or failed to read, prompt user
    print("\nPlease provide the path to the job posting text file.")
    print("Example: ./job_posting.txt")
    print("(Press Ctrl+C to exit)\n")
    
    while True:
        try:
            file_path = input("Enter file path: ").strip()
            if file_path.lower() in ['exit', 'quit', 'q']:
                raise KeyboardInterrupt
            
            try:
                return read_file_with_encodings(file_path)
            except FileReadError as e:
                print(f"Error: {str(e)}")
                print("Please try again or type 'exit' to quit.")
            except FileNotFoundError:
                print(f"Error: File '{file_path}' not found.")
                print("Please try again or type 'exit' to quit.")

        except KeyboardInterrupt:
            print("\nExiting application...")
            raise SystemExit(0)


def tailor_resume(client, resume_text, job_text, temperature):
    """Generate a tailored version of the resume for the job posting.
    
    Args:
        client: The OpenAI client instance.
        resume_text (str): The original resume content.
        job_text (str): The job posting content.
        temperature (float): Tailoring intensity between 0.0 and 1.0
        
    Returns:
        str: The tailored resume content.
    """
    # Create dynamic instructions based on temperature
    base_instructions = [
        {
            "action": "Keep original content and phrasing",
            "weight": 1.0 - temperature
        },
        {
            "action": "Adjust content to match job requirements",
            "weight": temperature
        },
        {
            "action": "Use industry-specific terminology",
            "weight": temperature
        },
        {
            "action": "Add relevant details to existing points",
            "weight": temperature
        },
        {
            "action": "Restructure content order for relevance",
            "weight": temperature * 0.8  # Less weight on structural changes
        }
    ]
    
    # Generate dynamic instructions string
    instructions = "\n".join([
        f"{i+1}. {item['action']} (Priority: {'High' if item['weight'] > 0.7 else 'Medium' if item['weight'] > 0.3 else 'Low'})"
        for i, item in enumerate(base_instructions)
    ])
    
    # Additional guidelines based on temperature
    preservation_note = f"Preserve approximately {int((1 - temperature) * 100)}% of the original content"
    matching_note = f"Match approximately {int(temperature * 100)}% of key terms and skills from the job posting"
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": f"""You are an expert at tailoring resumes to job descriptions.
                    
                    Tailoring Guidelines:
                    {instructions}
                    
                    Additional Instructions:
                    - {preservation_note}
                    - {matching_note}
                    - Maintain truthfulness - never fabricate experience
                    - Maintain the exact same formatting as the original resume
                    - Keep overall length similar to original
                    
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


def get_tailoring_temperature():
    """Get the desired level of resume tailoring.
    
    Returns:
        float: Tailoring temperature between 0.0 and 1.0
    """
    print("\nEnter tailoring level (0.0 to 1.0):")
    print("0.0: Minimal changes (preserve most of original)")
    print("0.5: Balanced changes")
    print("1.0: Extensive changes (closely match job posting)")
    print("Or any value in between")
    
    while True:
        try:
            temp = float(input("\nEnter value (0.0-1.0): ").strip())
            if 0.0 <= temp <= 1.0:
                return temp
            else:
                print("Please enter a value between 0.0 and 1.0")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nExiting application...")
            raise SystemExit(0)


def main():
    """Main execution function."""
    try:
        # Check environment variables
        check_environment()

        # Get base resume document ID
        doc_id = get_base_resume()

        # Initialize Google Docs service with retry on token error
        max_retries = 2
        for attempt in range(max_retries):
            try:
                creds = get_google_auth()
                docs_service = build('docs', 'v1', credentials=creds)
                # Test the credentials with a simple API call
                docs_service.documents().get(documentId=doc_id).execute()
                break  # If we get here, the credentials work
            except Exception as e:
                if 'invalid_grant' in str(e) and attempt < max_retries - 1:
                    logging.warning("Token validation failed, retrying authentication...")
                    if os.path.exists('token.pickle'):
                        os.remove('token.pickle')
                    continue
                raise  # Re-raise the exception if we're out of retries or it's a different error

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
        
        # Get tailoring temperature
        temperature = get_tailoring_temperature()
        
        # Generate tailored resume
        print("\nTailoring resume for the position...")
        tailored_content = tailor_resume(client, resume_content, job_content, temperature)
        
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
