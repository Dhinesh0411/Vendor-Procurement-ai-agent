"""
Email Agent - Autonomous email monitoring and processing.
Monitors incoming emails for procurement requests and vendor responses.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
from email_validator import validate_email
import re

logger = logging.getLogger(__name__)


class EmailAgent:
    """Monitor and process procurement-related emails."""
    
    def __init__(self, db, email_config: Dict):
        """
        Initialize email agent.
        
        Args:
            db: Database instance
            email_config: Email configuration dict with IMAP/SMTP settings
        """
        self.db = db
        self.email_config = email_config
        self.running = False
        self.process_queue = []
    
    async def start_monitoring(self, check_interval: int = 300):
        """
        Start autonomous email monitoring.
        
        Args:
            check_interval: Seconds between email checks
        """
        self.running = True
        logger.info("Email Agent started - monitoring enabled")
        
        while self.running:
            try:
                await self._check_emails()
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in email monitoring: {e}")
                await asyncio.sleep(check_interval)
    
    async def _check_emails(self):
        """Check for new emails and process them."""
        # Mock email fetching - In real implementation, use imaplib
        logger.debug("Checking for new emails...")
        
        # Simulate checking emails
        emails = self._simulate_email_fetch()
        
        for email_data in emails:
            await self._process_email(email_data)
    
    def _simulate_email_fetch(self) -> List[Dict]:
        """Simulate fetching emails from IMAP server."""
        # In production, use imaplib to connect to real email server
        return []
    
    async def _process_email(self, email_data: Dict):
        """
        Process an incoming email.
        
        Args:
            email_data: Email information (sender, subject, body, etc.)
        """
        try:
            sender = email_data.get('sender', '')
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            timestamp = email_data.get('timestamp', datetime.now())
            
            logger.info(f"Processing email from {sender}: {subject}")
            
            # Classify email type
            email_type = self._classify_email(subject, body)
            
            if email_type == 'procurement_request':
                await self._handle_procurement_request(sender, subject, body, timestamp)
            
            elif email_type == 'quotation':
                await self._handle_quotation(sender, subject, body, timestamp)
            
            elif email_type == 'order_confirmation':
                await self._handle_order_confirmation(sender, subject, body, timestamp)
            
            elif email_type == 'delivery_update':
                await self._handle_delivery_update(sender, subject, body, timestamp)
            
            elif email_type == 'complaint':
                await self._handle_complaint(sender, subject, body, timestamp)
            
            # Log communication
            vendor_id = self._get_vendor_id(sender)
            self.db.log_communication(
                vendor_id,
                'email',
                subject,
                body,
                'received'
            )
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
    
    def _classify_email(self, subject: str, body: str) -> str:
        """Classify email by type based on content."""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        # Keyword patterns
        if any(word in subject_lower for word in ['rfq', 'quotation request', 'price quote']):
            return 'quotation'
        elif any(word in subject_lower for word in ['order confirmation', 'po confirmed', 'order received']):
            return 'order_confirmation'
        elif any(word in subject_lower for word in ['shipped', 'delivery', 'tracking', 'in transit']):
            return 'delivery_update'
        elif any(word in subject_lower for word in ['complaint', 'issue', 'problem', 'defect', 'quality']):
            return 'complaint'
        elif any(word in subject_lower for word in ['purchase request', 'procurement', 'need to order']):
            return 'procurement_request'
        
        return 'other'
    
    async def _handle_procurement_request(self, sender: str, subject: str, 
                                         body: str, timestamp: datetime):
        """
        Handle procurement request email.
        
        Extracted items and quantities from email body.
        """
        logger.info(f"Processing procurement request from {sender}")
        
        # Extract items and quantities using NLP
        items = self._extract_items(body)
        
        for item in items:
            logger.info(f"Creating RFQ for: {item['name']}, qty: {item['quantity']}")
            
            # Create RFQ in database
            rfq_id = self.db.create_rfq(
                item_name=item['name'],
                quantity=item['quantity'],
                specifications=item.get('specifications', ''),
                deadline=datetime.now()
            )
            
            # Trigger extraction agent
            logger.info(f"RFQ {rfq_id} created - triggering extraction agent")
    
    async def _handle_quotation(self, sender: str, subject: str, 
                               body: str, timestamp: datetime):
        """Handle vendor quotation email."""
        logger.info(f"Processing quotation from {sender}")
        
        vendor_id = self._get_vendor_id(sender)
        if not vendor_id:
            logger.warning(f"Vendor not found for email: {sender}")
            return
        
        # Extract quotation details
        quotation_data = self._extract_quotation_details(body)
        
        logger.info(f"Quotation data extracted: {quotation_data}")
    
    async def _handle_order_confirmation(self, sender: str, subject: str,
                                        body: str, timestamp: datetime):
        """Handle order confirmation from vendor."""
        logger.info(f"Order confirmation from {sender}")
        
        vendor_id = self._get_vendor_id(sender)
        order_reference = self._extract_order_reference(body)
        
        if order_reference:
            logger.info(f"Order {order_reference} confirmed by vendor {vendor_id}")
    
    async def _handle_delivery_update(self, sender: str, subject: str,
                                     body: str, timestamp: datetime):
        """Handle delivery/shipment update from vendor."""
        logger.info(f"Delivery update from {sender}")
        
        vendor_id = self._get_vendor_id(sender)
        tracking_info = self._extract_tracking_info(body)
        
        logger.info(f"Tracking info: {tracking_info}")
    
    async def _handle_complaint(self, sender: str, subject: str,
                               body: str, timestamp: datetime):
        """Handle complaints or quality issues."""
        logger.warning(f"Complaint from {sender}: {subject}")
        
        vendor_id = self._get_vendor_id(sender)
        issue_description = body[:500]  # First 500 chars
        
        # Log complaint
        self.db.log_communication(
            vendor_id,
            'complaint',
            subject,
            issue_description,
            'received'
        )
        
        logger.warning(f"Complaint logged for vendor {vendor_id}")
    
    def _extract_items(self, body: str) -> List[Dict]:
        """Extract items and quantities from email body."""
        items = []
        
        # Pattern: "10 units of Widget" or "100 pcs of Item Name"
        patterns = [
            r'(\d+)\s*(?:units?|pcs?|pieces?|items?)\s+(?:of\s+)?([A-Za-z\s]+?)(?:\.|,|$)',
            r'order\s*:?\s*(\d+)\s+([A-Za-z\s]+?)(?:\.|,|$)',
            r'([A-Za-z\s]+?)\s*:\s*(\d+)\s*(?:units?|pcs?)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, body, re.IGNORECASE)
            for match in matches:
                if pattern == patterns[0]:
                    qty, name = match.groups()
                elif pattern == patterns[1]:
                    qty, name = match.groups()
                else:
                    name, qty = match.groups()
                
                items.append({
                    'name': name.strip(),
                    'quantity': int(qty),
                    'specifications': ''
                })
        
        return items
    
    def _extract_quotation_details(self, body: str) -> Dict:
        """Extract quotation details from email body."""
        quotation = {
            'unit_price': None,
            'delivery_days': None,
            'terms': ''
        }
        
        # Pattern for price: "$100" or "100 USD"
        price_pattern = r'(?:price|cost)\s*:?\s*\$?([\d.]+)'
        price_match = re.search(price_pattern, body, re.IGNORECASE)
        if price_match:
            quotation['unit_price'] = float(price_match.group(1))
        
        # Pattern for delivery: "7 days" or "delivery: 10 days"
        delivery_pattern = r'(?:delivery|lead time)\s*:?\s*(\d+)\s*(?:days|d)'
        delivery_match = re.search(delivery_pattern, body, re.IGNORECASE)
        if delivery_match:
            quotation['delivery_days'] = int(delivery_match.group(1))
        
        # Extract first 200 chars as terms
        quotation['terms'] = body[:200]
        
        return quotation
    
    def _extract_order_reference(self, body: str) -> Optional[str]:
        """Extract purchase order or reference number."""
        pattern = r'(?:PO|PO#|Order #|Reference)\s*:?\s*([A-Z0-9-]+)'
        match = re.search(pattern, body, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _extract_tracking_info(self, body: str) -> Dict:
        """Extract tracking information."""
        tracking = {
            'tracking_number': None,
            'carrier': None,
            'estimated_arrival': None
        }
        
        # Pattern for tracking number
        tracking_pattern = r'(?:tracking|shipment)\s*:?\s*([A-Z0-9]+)'
        tracking_match = re.search(tracking_pattern, body, re.IGNORECASE)
        if tracking_match:
            tracking['tracking_number'] = tracking_match.group(1)
        
        # Pattern for carrier
        for carrier in ['fedex', 'ups', 'dhl', 'usps']:
            if carrier.lower() in body.lower():
                tracking['carrier'] = carrier.upper()
                break
        
        return tracking
    
    def _get_vendor_id(self, email: str) -> Optional[int]:
        """Get vendor ID from email address."""
        try:
            # Remove domain to get vendor name or look up by email
            vendor_name = email.split('@')[0]
            return self.db.get_vendor_by_name(vendor_name)
        except:
            return None
    
    async def send_rfq_to_vendors(self, rfq_id: int, vendors: List[Dict], 
                                 subject: str, body: str):
        """
        Send RFQ to multiple vendors.
        
        Args:
            rfq_id: Request for quotation ID
            vendors: List of vendor dicts with email
            subject: Email subject
            body: Email body
        """
        for vendor in vendors:
            vendor_email = vendor.get('email')
            if vendor_email:
                logger.info(f"Sending RFQ {rfq_id} to {vendor_email}")
                
                # Log communication
                self.db.log_communication(
                    vendor['vendor_id'],
                    'rfq',
                    subject,
                    body,
                    'sent'
                )
                
                # In production, actually send email via SMTP
                await asyncio.sleep(0.1)  # Simulate send delay
    
    def stop_monitoring(self):
        """Stop email monitoring."""
        self.running = False
        logger.info("Email Agent stopped")
