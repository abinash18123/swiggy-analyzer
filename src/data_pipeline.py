"""
Data pipeline for collecting Swiggy order data from email text
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
        
    def run_pipeline(self, max_emails: int = 500):
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
        
        for i, message in enumerate(messages, 1):
            message_id = message['id']
            print(f"\nProcessing email {i}/{len(messages)} (ID: {message_id})")
            
            # Get email details
            email_data = self.gmail_client.get_email_details(message_id)
            if not email_data:
                print(f"  ❌ Failed to get email details")
                continue
            
            # Print full email details for the first email
            if i == 1:
                print("\nFull Email Details:")
                print("Subject:", email_data.get('subject', ''))
                print("From:", email_data.get('from', ''))
                print("Date:", email_data.get('date', ''))
                print("\nEmail body:")
                print(email_data.get('body', ''))
                print("\n" + "="*50 + "\n")
            
            # Parse email body
            email_body = email_data.get('body', '')
            order_info = self.email_parser.parse_email(email_body)
            
            if not order_info:
                print(f"  ❌ Failed to parse email/Instacart order")
                continue
                
            order_info['email_id'] = message_id
            processed_orders.append(order_info)
            print(f"  ✅ Successfully processed")
        
        # Step 3: Save to CSV
        if processed_orders:
            self._save_to_csv(processed_orders)
            print(f"\n✅ Successfully processed {len(processed_orders)} orders")
        else:
            print("\n❌ No orders were successfully processed")
    
    def _save_to_csv(self, orders: List[Dict]):
        """Save processed orders to CSV"""
        fieldnames = [
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
    pipeline.run_pipeline(max_emails=500)  # Process all emails

if __name__ == "__main__":
    main()
