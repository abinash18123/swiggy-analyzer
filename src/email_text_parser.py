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
            # Remove ₹ symbol, any commas, and handle negative amounts (discounts)
            amount = amount_str.replace('₹', '').replace(',', '').strip()
            if amount.startswith('-'):
                amount = amount[1:]  # Remove minus sign
            return float(amount)
        except (ValueError, AttributeError):
            return 0.0

    def parse_email(self, email_text: str) -> dict:
        """Parse Swiggy delivery email text to extract order details"""
        if not email_text:
            return None

        # Convert HTML to clean text while preserving some structure
        soup = BeautifulSoup(email_text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text with preserved line breaks
        text = soup.get_text(separator='\n')
        
        # Clean up text
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not line.isspace():
                lines.append(line)

        order_info = {
            'restaurant_name': None,
            'order_time': None,
            'delivery_time': None,
            'delivery_duration_mins': None,
            'total_amount': None,
            'discount_amount': 0.0
        }

        # Extract restaurant name
        restaurant_found = False
        for i, line in enumerate(lines):
            if line == "Restaurant":
                for next_line in lines[i+1:]:
                    if next_line and next_line not in ["Order", "Your Order Summary:", "Order No:"]:
                        order_info['restaurant_name'] = next_line
                        restaurant_found = True
                        break
                if restaurant_found:
                    break

        # Extract order and delivery times
        for i, line in enumerate(lines):
            if "Order placed at:" in line:
                # Look for the datetime in this line or the next few lines
                for j in range(i, min(i + 3, len(lines))):
                    possible_date = lines[j].replace("Order placed at:", "").strip()
                    parsed_date = self.parse_datetime(possible_date)
                    if parsed_date:
                        order_info['order_time'] = parsed_date
                        break
            
            elif "Order delivered at:" in line:
                # Look for the datetime in this line or the next few lines
                for j in range(i, min(i + 3, len(lines))):
                    possible_date = lines[j].replace("Order delivered at:", "").strip()
                    parsed_date = self.parse_datetime(possible_date)
                    if parsed_date:
                        order_info['delivery_time'] = parsed_date
                        break

        # Calculate delivery duration
        if order_info['order_time'] and order_info['delivery_time']:
            duration = order_info['delivery_time'] - order_info['order_time']
            order_info['delivery_duration_mins'] = duration.total_seconds() / 60

        # Extract amounts using more flexible patterns
        for i, line in enumerate(lines):
            # Look for total amount
            if "Order Total:" in line or "Paid Via" in line:
                # Check this line and next few lines for amount
                for j in range(i, min(i + 3, len(lines))):
                    if '₹' in lines[j]:
                        amount = self.extract_amount(lines[j])
                        if amount > 0:  # Sanity check
                            order_info['total_amount'] = amount
                            break

            # Look for discount
            if "Discount Applied" in line:
                # Check this line and next few lines for amount
                for j in range(i, min(i + 3, len(lines))):
                    if '₹' in lines[j] and '-' in lines[j]:
                        order_info['discount_amount'] = self.extract_amount(lines[j])
                        break

        # Additional validation
        if not order_info['total_amount']:
            # Try finding total amount by looking for specific patterns
            for line in lines:
                if "Order Total:" in line or "Paid Via" in line or "Total Payable:" in line:
                    amounts = re.findall(r'₹\s*[\d,]+(?:\.\d{2})?', line)
                    if amounts:
                        order_info['total_amount'] = self.extract_amount(amounts[0])
                        break

        # Validate required fields
        if not all([
            order_info['restaurant_name'],
            order_info['order_time'],
            order_info['delivery_time'],
            order_info['total_amount'] is not None
        ]):
            return None

        return order_info