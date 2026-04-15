"""
Extraction Agent - Process procurement requests and create RFQs.
Handles extraction of procurement requirements and vendor outreach.
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ExtractionAgent:
    """Extract procurement requirements and manage RFQs."""
    
    def __init__(self, db, email_agent=None):
        """
        Initialize extraction agent.
        
        Args:
            db: Database instance
            email_agent: Email agent instance for sending RFQs
        """
        self.db = db
        self.email_agent = email_agent
        self.active_rfqs = {}
    
    async def process_procurement_request(self, request_data: Dict) -> Dict:
        """
        Process a procurement request.
        
        Args:
            request_data: Contains item_name, quantity, specifications, etc.
            
        Returns:
            RFQ details
        """
        try:
            item_name = request_data.get('item_name', '')
            quantity = request_data.get('quantity', 0)
            specifications = request_data.get('specifications', '')
            priority = request_data.get('priority', 'normal')
            budget = request_data.get('budget', 0)
            
            logger.info(f"Processing procurement request: {item_name}, qty: {quantity}")
            
            # Check inventory first
            existing_stock = self._check_inventory(item_name)
            
            if existing_stock >= quantity:
                logger.info(f"Sufficient inventory found for {item_name}")
                return {
                    'status': 'fulfilled_from_inventory',
                    'item_name': item_name,
                    'quantity': quantity,
                    'source': 'inventory'
                }
            
            # Calculate procurement quantity
            shortage = quantity - existing_stock
            order_quantity = self._calculate_order_quantity(shortage, item_name)
            
            # Create RFQ
            deadline = self._calculate_deadline(priority)
            rfq_id = self.db.create_rfq(
                item_name=item_name,
                quantity=order_quantity,
                specifications=specifications,
                deadline=deadline
            )
            
            logger.info(f"RFQ {rfq_id} created for {item_name} (qty: {order_quantity})")
            
            # Get suitable vendors
            suitable_vendors = await self._identify_suitable_vendors(
                item_name, specifications, priority
            )
            
            logger.info(f"Found {len(suitable_vendors)} suitable vendors")
            
            # Send RFQ to vendors
            if self.email_agent:
                await self._send_rfq_to_vendors(
                    rfq_id, suitable_vendors, item_name, order_quantity
                )
            
            self.active_rfqs[rfq_id] = {
                'item_name': item_name,
                'quantity': order_quantity,
                'budget': budget,
                'priority': priority,
                'created_at': datetime.now(),
                'deadline': deadline,
                'vendors_contacted': len(suitable_vendors),
                'status': 'active'
            }
            
            return {
                'status': 'rfq_created',
                'rfq_id': rfq_id,
                'item_name': item_name,
                'quantity': order_quantity,
                'vendors_contacted': len(suitable_vendors),
                'deadline': deadline.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing procurement request: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _check_inventory(self, item_name: str) -> int:
        """Check current inventory for item."""
        # Query database for inventory
        conn = self.db.db_path  # Access DB connection
        return 0  # Simplified - actual implementation queries DB
    
    def _calculate_order_quantity(self, shortage: int, item_name: str) -> int:
        """Calculate optimal order quantity using EOQ approach."""
        # Add buffer stock (20% additional)
        buffer = int(shortage * 0.20) + 5
        return shortage + buffer
    
    def _calculate_deadline(self, priority: str) -> datetime:
        """Calculate RFQ response deadline based on priority."""
        priority_days = {
            'urgent': 1,
            'high': 3,
            'normal': 7,
            'low': 14
        }
        days = priority_days.get(priority, 7)
        return datetime.now() + timedelta(days=days)
    
    async def _identify_suitable_vendors(self, item_name: str, 
                                        specifications: str,
                                        priority: str) -> List[Dict]:
        """
        Identify suitable vendors for the procurement.
        
        Args:
            item_name: Item to procure
            specifications: Technical specifications
            priority: Procurement priority
            
        Returns:
            List of suitable vendors
        """
        # Get all active vendors
        vendors = self.db.get_all_vendors()
        
        # Filter based on criteria
        suitable_vendors = []
        
        for vendor in vendors:
            # Skip vendors with poor ratings
            if vendor.get('rating', 0) < 3.0:
                continue
            
            # Prioritize vendors in category
            vendor_category = vendor.get('category', '')
            if vendor_category and vendor_category.lower() in item_name.lower():
                suitable_vendors.append(vendor)
            elif vendor.get('status') == 'active':
                suitable_vendors.append(vendor)
        
        # Sort by rating
        suitable_vendors.sort(key=lambda v: v.get('rating', 0), reverse=True)
        
        # For urgent orders, limit to top vendors; for normal, expand list
        if priority == 'urgent':
            return suitable_vendors[:5]
        elif priority == 'high':
            return suitable_vendors[:10]
        else:
            return suitable_vendors[:15]
    
    async def _send_rfq_to_vendors(self, rfq_id: int, vendors: List[Dict],
                                  item_name: str, quantity: int):
        """
        Send RFQ emails to vendors.
        
        Args:
            rfq_id: RFQ ID
            vendors: List of vendors
            item_name: Item name
            quantity: Required quantity
        """
        subject = f"Request for Quotation: {item_name} (RFQ#{rfq_id})"
        
        body = f"""
Dear Vendor,

We are requesting your quotation for the following:

Item: {item_name}
Quantity: {quantity} units
RFQ Reference: RFQ#{rfq_id}

Please provide:
1. Unit price
2. Estimated delivery time
3. Payment terms
4. Any applicable discounts for bulk orders

Please reply with your quotation within the specified deadline.

Best regards,
Procurement Department
        """
        
        if self.email_agent:
            await self.email_agent.send_rfq_to_vendors(
                rfq_id, vendors, subject, body
            )
    
    async def monitor_rfq_responses(self, check_interval: int = 60):
        """
        Monitor RFQ responses and trigger decision agent when needed.
        
        Args:
            check_interval: Seconds between checks
        """
        logger.info("RFQ monitoring started")
        
        while True:
            try:
                for rfq_id in list(self.active_rfqs.keys()):
                    rfq_data = self.active_rfqs[rfq_id]
                    
                    # Get quotations for this RFQ
                    quotations = self.db.get_rfq_quotations(rfq_id)
                    
                    # Check deadline
                    if datetime.now() > rfq_data['deadline']:
                        logger.info(f"RFQ {rfq_id} deadline reached")
                        rfq_data['status'] = 'closed'
                        
                        # Trigger decision agent
                        await self._trigger_decision_agent(rfq_id, quotations)
                        
                        del self.active_rfqs[rfq_id]
                    
                    # Or if enough quotations received (decision rule)
                    elif len(quotations) >= rfq_data['vendors_contacted'] * 0.5:
                        if len(quotations) >= 3:  # Minimum quotations
                            logger.info(f"Minimum quotations reached for {rfq_id}")
                            rfq_data['status'] = 'ready_for_decision'
                            
                            await self._trigger_decision_agent(rfq_id, quotations)
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring RFQs: {e}")
                await asyncio.sleep(check_interval)
    
    async def _trigger_decision_agent(self, rfq_id: int, quotations: List[Dict]):
        """Trigger decision agent to select best quotation."""
        logger.info(f"Triggering decision agent for RFQ {rfq_id} with {len(quotations)} quotations")
        
        # This would be called by the main orchestrator
        # For now, just log the event
        return {
            'rfq_id': rfq_id,
            'quotation_count': len(quotations),
            'ready_for_decision': True
        }
    
    def get_rfq_status(self, rfq_id: int) -> Dict:
        """Get status of an RFQ."""
        if rfq_id not in self.active_rfqs:
            return {'status': 'unknown', 'rfq_id': rfq_id}
        
        rfq_data = self.active_rfqs[rfq_id]
        quotations = self.db.get_rfq_quotations(rfq_id)
        
        time_remaining = (rfq_data['deadline'] - datetime.now()).total_seconds() / 3600
        
        return {
            'rfq_id': rfq_id,
            'item_name': rfq_data['item_name'],
            'quantity': rfq_data['quantity'],
            'status': rfq_data['status'],
            'quotations_received': len(quotations),
            'vendors_contacted': rfq_data['vendors_contacted'],
            'hours_until_deadline': max(0, time_remaining),
            'priority': rfq_data['priority']
        }
