"""
Gmail API client for fetching Swiggy emails
"""
import os
import base64
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import Config

class GmailClient:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self):
        self.creds = self._get_credentials()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def _get_credentials(self) -> Credentials:
        """Get valid user credentials from storage or user."""
        creds = None
        
        # Check if token.json exists
        if os.path.exists(Config.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(Config.TOKEN_FILE, self.SCOPES)

        # If no valid credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(Config.CREDENTIALS_FILE):
                    raise FileNotFoundError("Please place your Gmail API credentials file at credentials.json")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.CREDENTIALS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(Config.TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        return creds

    def search_swiggy_emails(self, max_results: int = 500) -> List[Dict]:
        """Search for Swiggy delivery confirmation emails"""
        query = f'from:{Config.SWIGGY_SENDER}'
        
        # Add subject keywords to query
        subject_terms = [f'subject:"{keyword}"' for keyword in Config.DELIVERY_SUBJECT_KEYWORDS]
        query += f' AND ({" OR ".join(subject_terms)})'
        
        # Add date range if specified
        if Config.START_DATE:
            query += f' AND after:{Config.START_DATE.replace("/", "-")}'
        if Config.END_DATE:
            query += f' AND before:{Config.END_DATE.replace("/", "-")}'

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            return results.get('messages', [])
        except Exception as e:
            print(f"Error searching emails: {str(e)}")
            return []

    def get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get email details including body text"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            email_data = {
                'id': message_id,
                'subject': '',
                'from': '',
                'date': '',
                'body': ''
            }

            # Get headers
            for header in message['payload']['headers']:
                name = header['name'].lower()
                if name == 'subject':
                    email_data['subject'] = header['value']
                elif name == 'from':
                    email_data['from'] = header['value']
                elif name == 'date':
                    email_data['date'] = header['value']

            # Get email body
            email_data['body'] = self._extract_email_body(message['payload'])
            return email_data

        except Exception as e:
            print(f"Error getting email details: {str(e)}")
            return None

    def _extract_email_body(self, payload: Dict) -> str:
        """Recursively extract email body from message payload"""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode()
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'].startswith('text/'):
                    if 'data' in part['body']:
                        text = base64.urlsafe_b64decode(part['body']['data']).decode()
                        if part['mimeType'] == 'text/html':
                            # Convert HTML to plain text
                            soup = BeautifulSoup(text, 'html.parser')
                            return soup.get_text()
                        return text
                elif part['mimeType'].startswith('multipart/'):
                    return self._extract_email_body(part)
        
        return ""
