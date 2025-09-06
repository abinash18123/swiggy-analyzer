"""
Simplified data pipeline for collecting Swiggy order data from email text
"""
import os
import csv
from datetime import datetime
from typing import List, Dict, Optional

from config import Config
from gmail_client import GmailClient
from email_text_parser import SwiggyEmailParser

class SwiggyDataPipeline:
    def __init__(self):
        self.gmail_client = GmailClient()
        self.email_parser = SwiggyEmailParser()
        self.csv_orders_file = os.path.join(Config.BASE_DIR, 'swiggy_orders.csv')
        
    def run_pipeline(self, max_emails: int = 5000):
        """Run the email processing pipeline"""
        print("🚀 Starting Swiggy Data Pipeline...")
        
        # Step 1: Search for emails
        print("\n📧 Step 1: Searching for Swiggy delivery emails...")
        messages = self.gmail_client.search_swiggy_emails(max_emails)
        print(f"Found {len(messages)} emails to process")
        
        if not messages:
            print("No emails found. Please check your Gmail API setup and search criteria.")
            return
        
        # Step 2: Process each email
        print("\n🔄 Step 2: Processing emails...")
        processed_orders = []
        failed_emails = []
        
        for i, message in enumerate(messages, 1):
            message_id = message['id']
            print(f"\n{'='*80}")
            print(f"Processing email {i}/{len(messages)} (ID: {message_id})")
            print(f"{'='*80}")
            
            # Get email details
            email_data = self.gmail_client.get_email_details(message_id)
            if not email_data:
                print(f"  ❌ Failed to get email details")
                continue
            
            # Print email details for debugging
            print("\nEmail Details:")
            print(f"Subject: {email_data.get('subject', '')}")
            print(f"From: {email_data.get('from', '')}")
            print(f"Date: {email_data.get('date', '')}")
            print("\nEmail Content Markers Found:")
            
            # Check for content markers
            for marker in Config.ORDER_CONTENT_MARKERS:
                if marker in email_data.get('body', ''):
                    print(f"✅ Found: {marker}")
                else:
                    print(f"❌ Missing: {marker}")
            
            # Parse email body
            email_body = email_data.get('body', '')
            order_info = self.email_parser.parse_email(email_body)
            
            if not order_info:
                print(f"\n❌ Failed to parse email")
                print("\nExtracted Fields:")
                # Try parsing anyway to see what we got
                temp_info = self.email_parser.parse_email(email_body, debug=True)
                if temp_info:
                    for key, value in temp_info.items():
                        print(f"{key}: {value}")
                failed_emails.append({
                    'id': message_id,
                    'subject': email_data.get('subject', ''),
                    'date': email_data.get('date', '')
                })
                continue
                
            print("\n✅ Successfully parsed email")
            print("\nExtracted Order Details:")
            for key, value in order_info.items():
                print(f"{key}: {value}")
                
            order_info['email_id'] = message_id
            processed_orders.append(order_info)
        
        # Step 3: Save to CSV
        if processed_orders:
            self._save_to_csv(processed_orders)
            print(f"\n✅ Successfully processed {len(processed_orders)} orders")
            success_rate = (len(processed_orders) / len(messages)) * 100
            print(f"Success rate: {success_rate:.2f}%")
        else:
            print("\n❌ No orders were successfully processed")
            
        # Print failed email summary
        if failed_emails:
            print("\nFailed Emails Summary:")
            print(f"Total failed: {len(failed_emails)}")
            print("\nFirst 5 failed emails:")
            for email in failed_emails[:5]:
                print(f"\nID: {email['id']}")
                print(f"Subject: {email['subject']}")
                print(f"Date: {email['date']}")
    
    def _save_to_csv(self, orders: List[Dict]):
        """Save processed orders to CSV"""
        fieldnames = [
            'email_id',
            'restaurant_name',
            'order_time',
            'delivery_time',
            'delivery_duration_mins',
            'total_amount',
            'discount_amount'
        ]
        
        try:
            with open(self.csv_orders_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for order in orders:
                    row = {
                        'email_id': order.get('email_id'),
                        'restaurant_name': order.get('restaurant_name'),
                        'order_time': order.get('order_time').strftime('%Y-%m-%d %H:%M:%S') if order.get('order_time') else None,
                        'delivery_time': order.get('delivery_time').strftime('%Y-%m-%d %H:%M:%S') if order.get('delivery_time') else None,
                        'delivery_duration_mins': order.get('delivery_duration_mins'),
                        'total_amount': order.get('total_amount'),
                        'discount_amount': order.get('discount_amount', 0.0)
                    }
                    writer.writerow(row)
                    
            print(f"\n📄 Saved {len(orders)} orders to {self.csv_orders_file}")
            
        except Exception as e:
            print(f"❌ Error saving to CSV: {str(e)}")

def main():
    """Main function to run the data pipeline"""
    pipeline = SwiggyDataPipeline()
    pipeline.run_pipeline(max_emails=5000)  # Increased max emails

if __name__ == "__main__":
    main()