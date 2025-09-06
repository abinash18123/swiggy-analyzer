"""
Gmail API client for fetching Swiggy emails
"""
import os
import base64
import time
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config

class GmailClient:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

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
        # Primary search is based on sender
        query = f'from:{Config.SWIGGY_SENDER}'
        
        # Add date range if specified
        if Config.START_DATE:
            query += f' AND after:{Config.START_DATE.replace("/", "-")}'
        if Config.END_DATE:
            query += f' AND before:{Config.END_DATE.replace("/", "-")}'

        print(f"\nSearching with query: {query}")
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(max_results, 500)  # Gmail API max per request
            ).execute()

            messages = results.get('messages', [])
            total_found = len(messages)
            print(f"Initial batch found: {total_found} messages")
            
            # If we got max_results, there might be more
            page_count = 1
            while 'nextPageToken' in results and len(messages) < max_results:
                page_count += 1
                print(f"\nFetching page {page_count}...")
                
                try:
                    results = self.service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=min(max_results - len(messages), 500),
                        pageToken=results['nextPageToken']
                    ).execute()
                    new_messages = results.get('messages', [])
                    messages.extend(new_messages)
                    print(f"Found {len(new_messages)} more messages (Total: {len(messages)})")
                except HttpError as e:
                    print(f"Error fetching page {page_count}: {str(e)}")
                    break

            return messages
        except Exception as e:
            print(f"Error searching emails: {str(e)}")
            return []

    def get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get email details including body text"""
        for attempt in range(self.MAX_RETRIES):
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

                if 'payload' not in message:
                    print(f"No payload in message: {message_id}")
                    return None

                if 'headers' not in message['payload']:
                    print(f"No headers in message payload: {message_id}")
                    return None

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
                
                if not email_data['body']:
                    print(f"Could not extract body from message: {message_id}")
                    print("Message payload structure:", message['payload'].keys())
                    return None

                # Print email details for debugging
                print("\nEmail Details:")
                print(f"From: {email_data['from']}")
                print(f"Subject: {email_data['subject']}")
                print(f"Date: {email_data['date']}")
                print("\nBody Preview (first 200 chars):")
                print(email_data['body'][:200] + "...")

                # Validate this is a Swiggy order email by checking content markers
                if not self._is_valid_order_email(email_data):
                    print(f"\nEmail validation failed for {message_id}")
                    return None
                    
                return email_data

            except HttpError as e:
                if e.resp.status == 429:  # Rate limit exceeded
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = (attempt + 1) * self.RETRY_DELAY
                        print(f"Rate limit hit, waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                print(f"HTTP Error getting email {message_id}: {str(e)}")
                return None
            except Exception as e:
                print(f"Error getting email {message_id}: {str(e)}")
                return None
        
        return None

    def _extract_email_body(self, payload: Dict) -> str:
        """Recursively extract email body from message payload"""
        try:
            if 'body' in payload and payload['body'].get('data'):
                return base64.urlsafe_b64decode(payload['body']['data']).decode()
            
            if 'parts' in payload:
                # First try to find HTML content
                for part in payload['parts']:
                    if part['mimeType'] == 'text/html' and 'data' in part.get('body', {}):
                        try:
                            text = base64.urlsafe_b64decode(part['body']['data']).decode()
                            return text
                        except Exception as e:
                            print(f"Error decoding HTML part: {str(e)}")
                            continue
                
                # If no HTML, try other text content
                for part in payload['parts']:
                    if part['mimeType'].startswith('text/'):
                        if 'data' in part.get('body', {}):
                            try:
                                return base64.urlsafe_b64decode(part['body']['data']).decode()
                            except Exception as e:
                                print(f"Error decoding text part: {str(e)}")
                                continue
                    elif part['mimeType'].startswith('multipart/'):
                        body = self._extract_email_body(part)
                        if body:
                            return body
            
            print("Could not find any text content in payload")
            return ""
            
        except Exception as e:
            print(f"Error extracting email body: {str(e)}")
            return ""

    def _is_valid_order_email(self, email_data: Dict) -> bool:
        """
        Validate if this is a Swiggy order email by checking for specific content markers
        rather than relying solely on email subject
        """
        # Check sender - look for noreply@swiggy.in in the From field
        if Config.SWIGGY_SENDER not in email_data['from']:
            print(f"Invalid sender: {email_data['from']}")
            return False
            
        body = email_data['body']
        if not body:
            print("Empty email body")
            return False
            
        # Check for presence of key order content markers
        markers_found = []
        for marker in Config.ORDER_CONTENT_MARKERS:
            if marker in body:
                markers_found.append(marker)
                
        # Print found markers for debugging
        print("\nContent markers found:")
        for marker in markers_found:
            print(f"✓ {marker}")
        
        missing_markers = [m for m in Config.ORDER_CONTENT_MARKERS if m not in markers_found]
        if missing_markers:
            print("\nMissing markers:")
            for marker in missing_markers:
                print(f"✗ {marker}")
                
        # Require at least 3 markers to consider it a valid order email
        if len(markers_found) < 3:
            print(f"\nInsufficient markers: found {len(markers_found)}, need at least 3")
            return False
            
        return True