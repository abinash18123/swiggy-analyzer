"""
Parser for Swiggy delivery confirmation emails
"""
from datetime import datetime
from bs4 import BeautifulSoup
import re

class SwiggyEmailParser:
    def parse_datetime(self, datetime_str: str) -> datetime:
        """Parse Swiggy's datetime format"""
        try:
            return datetime.strptime(datetime_str.strip(), "%A, %B %d, %Y %I:%M %p")
        except (ValueError, AttributeError):
            return None

    def extract_amount(self, amount_str: str) -> float:
        """Extract amount from string with ₹ symbol"""
        try:
            # Remove ₹ symbol and any commas, then convert to float
            amount = amount_str.replace('₹', '').replace(',', '').strip()
            return float(amount)
        except (ValueError, AttributeError):
            return 0.0

    def parse_email(self, email_text: str) -> dict:
        """Parse Swiggy delivery email text to extract order details"""
        if not email_text:
            return None

        # Convert HTML to clean text
        soup = BeautifulSoup(email_text, 'html.parser')
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        order_info = {
            'restaurant_name': None,
            'order_time': None,
            'delivery_time': None,
            'delivery_duration_mins': None,
            'total_amount': None,
            'discount_amount': 0.0
        }

        # Extract restaurant name
        for i, line in enumerate(lines):
            if line == "Restaurant":
                for next_line in lines[i+1:]:
                    if next_line and next_line not in ["Order", "Your Order Summary:"]:
                        order_info['restaurant_name'] = next_line
                        break

        # Extract order and delivery times
        for i, line in enumerate(lines):
            if line == "Order placed at:":
                for next_line in lines[i+1:]:
                    if next_line:
                        order_info['order_time'] = self.parse_datetime(next_line)
                        break
            elif line == "Order delivered at:":
                for next_line in lines[i+1:]:
                    if next_line:
                        order_info['delivery_time'] = self.parse_datetime(next_line)
                        break

        # Calculate delivery duration
        if order_info['order_time'] and order_info['delivery_time']:
            duration = order_info['delivery_time'] - order_info['order_time']
            order_info['delivery_duration_mins'] = duration.total_seconds() / 60

        # Extract amounts
        for i, line in enumerate(lines):
            if line == "Order Total:":
                for next_line in lines[i+1:]:
                    if next_line:
                        order_info['total_amount'] = self.extract_amount(next_line)
                        break
            elif "Discount Applied" in line:
                for next_line in lines[i+1:]:
                    if next_line:
                        order_info['discount_amount'] = self.extract_amount(next_line)
                        break

        # Validate required fields
        if not all([order_info['restaurant_name'], 
                   order_info['order_time'],
                   order_info['delivery_time'],
                   order_info['total_amount'] is not None]):
            return None

        return order_info
