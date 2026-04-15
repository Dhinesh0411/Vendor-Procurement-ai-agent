"""
Follow-up Agent - Vendor relationship management and follow-ups.
Manages vendor communications, ratings, and relationship improvements.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FollowupAgent:
    """Manage vendor relationships and follow-ups."""
    
    def __init__(self, db, email_agent=None):
        """
        Initialize follow-up agent.
        
        Args:
            db: Database instance
            email_agent: Email agent for sending communications
        """
        self.db = db
        self.email_agent = email_agent
    
    async def process_pending_followups(self, check_interval: int = 3600):
        """
        Process pending follow-ups.
        
        Args:
            check_interval: Seconds between checks
        """
        logger.info("Follow-up agent started")
        
        while True:
            try:
                # Check for orders needing follow-up
                followup_tasks = await self._identify_followup_tasks()
                
                for task in followup_tasks:
                    await self._execute_followup(task)
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error processing follow-ups: {e}")
                await asyncio.sleep(check_interval)
    
    async def _identify_followup_tasks(self) -> List[Dict]:
        """
        Identify pending follow-up tasks.
        
        Returns:
            List of follow-up tasks
        """
        tasks = []
        
        # Get all active vendors
        vendors = self.db.get_all_vendors()
        
        for vendor in vendors:
            vendor_id = vendor['vendor_id']
            
            # Get vendor's orders
            orders = self.db.get_orders_by_vendor(vendor_id)
            
            for order in orders:
                order_id = order['order_id']
                status = order['status']
                order_date = order['order_date']
                
                # Follow-up rule 1: Check for pending orders older than 5 days
                if status == 'pending':
                    days_pending = (datetime.now() - order_date).days
                    if days_pending > 5:
                        tasks.append({
                            'type': 'check_pending_order',
                            'vendor_id': vendor_id,
                            'order_id': order_id,
                            'priority': 'high'
                        })
                
                # Follow-up rule 2: Check for unconfirmed orders
                elif status == 'submitted':
                    days_since_order = (datetime.now() - order_date).days
                    if days_since_order > 3:
                        tasks.append({
                            'type': 'confirm_order',
                            'vendor_id': vendor_id,
                            'order_id': order_id,
                            'priority': 'medium'
                        })
            
            # Follow-up rule 3: Rate poorly performing vendors
            if vendor.get('rating', 5) < 3.0:
                tasks.append({
                    'type': 'performance_review',
                    'vendor_id': vendor_id,
                    'priority': 'high'
                })
            
            # Follow-up rule 4: Recognize high performers
            if vendor.get('rating', 0) >= 4.5:
                tasks.append({
                    'type': 'appreciation_email',
                    'vendor_id': vendor_id,
                    'priority': 'low'
                })
        
        return tasks
    
    async def _execute_followup(self, task: Dict):
        """Execute a follow-up task."""
        task_type = task.get('type')
        vendor_id = task.get('vendor_id')
        
        try:
            if task_type == 'check_pending_order':
                await self._followup_pending_order(vendor_id, task['order_id'])
            
            elif task_type == 'confirm_order':
                await self._confirm_order_receipt(vendor_id, task['order_id'])
            
            elif task_type == 'performance_review':
                await self._send_performance_review(vendor_id)
            
            elif task_type == 'appreciation_email':
                await self._send_appreciation_email(vendor_id)
            
        except Exception as e:
            logger.error(f"Error executing follow-up task {task_type}: {e}")
    
    async def _followup_pending_order(self, vendor_id: int, order_id: int):
        """Send follow-up for pending order."""
        logger.info(f"Following up on pending order {order_id} from vendor {vendor_id}")
        
        vendors = self.db.get_all_vendors()
        vendor = next((v for v in vendors if v['vendor_id'] == vendor_id), None)
        
        if not vendor:
            return
        
        subject = f"Status Update Request: Order PO#{order_id:06d}"
        body = f"""
Dear {vendor.get('name', 'Valued Vendor')},

We would like to obtain a status update on the following order:

PO Number: PO#{order_id:06d}
Status: Pending

Could you please provide:
1. Current status of the order
2. Estimated shipment/delivery date
3. Any issues or delays, if applicable

Please reply at your earliest convenience.

Best regards,
Procurement Department
        """
        
        self.db.log_communication(
            vendor_id,
            'followup',
            subject,
            body,
            'sent'
        )
    
    async def _confirm_order_receipt(self, vendor_id: int, order_id: int):
        """Send order receipt confirmation request."""
        logger.info(f"Requesting order confirmation for {order_id}")
        
        vendors = self.db.get_all_vendors()
        vendor = next((v for v in vendors if v['vendor_id'] == vendor_id), None)
        
        if not vendor:
            return
        
        subject = f"Order Confirmation Needed: PO#{order_id:06d}"
        body = f"""
Dear {vendor.get('name', 'Valued Vendor')},

We sent a purchase order and would like to confirm its receipt and acceptance.

PO Number: PO#{order_id:06d}

Please confirm by replying with:
1. Order acceptance
2. Expected production/shipment timeline
3. Any clarifications or concerns

Thank you,
Procurement Department
        """
        
        self.db.log_communication(
            vendor_id,
            'confirmation_request',
            subject,
            body,
            'sent'
        )
    
    async def _send_performance_review(self, vendor_id: int):
        """Send performance review/improvement letter to underperforming vendor."""
        logger.warning(f"Sending performance review to vendor {vendor_id}")
        
        vendors = self.db.get_all_vendors()
        vendor = next((v for v in vendors if v['vendor_id'] == vendor_id), None)
        
        if not vendor:
            return
        
        orders = self.db.get_orders_by_vendor(vendor_id)
        
        # Calculate metrics
        total = len(orders)
        on_time = sum(1 for o in orders if o['status'] == 'delivered')
        avg_quality = sum(o.get('quality_rating', 3) for o in orders if o.get('quality_rating')) / max(1, sum(1 for o in orders if o.get('quality_rating')))
        
        subject = f"Performance Discussion - {vendor.get('name')}"
        body = f"""
Dear {vendor.get('name', 'Valued Vendor')},

We appreciate our business relationship and would like to discuss recent performance metrics:

PERFORMANCE SUMMARY:
- Total Orders: {total}
- On-Time Delivery Rate: {(on_time/max(1,total)*100):.1f}%
- Average Quality Rating: {avg_quality:.1f}/5

We believe there are opportunities to improve our partnership. Areas for improvement:
1. Delivery timeliness
2. Quality consistency
3. Communication responsiveness

We would like to schedule a call to discuss:
- Your current challenges
- Our expectations
- Action plan for improvement
- Support we can provide

Please let us know your availability for a 30-minute call within the next week.

Best regards,
Procurement Department
        """
        
        self.db.log_communication(
            vendor_id,
            'performance_review',
            subject,
            body,
            'sent'
        )
    
    async def _send_appreciation_email(self, vendor_id: int):
        """Send appreciation/recognition email to high-performing vendor."""
        logger.info(f"Sending appreciation email to vendor {vendor_id}")
        
        vendors = self.db.get_all_vendors()
        vendor = next((v for v in vendors if v['vendor_id'] == vendor_id), None)
        
        if not vendor:
            return
        
        subject = f"Thank You - Continued Excellence - {vendor.get('name')}"
        body = f"""
Dear {vendor.get('name', 'Valued Vendor')},

We want to express our appreciation for your continued excellence in partnering with us.

Your Performance Highlights:
- Consistent on-time delivery: {vendor.get('on_time_delivery_rate', 0):.1f}%
- Outstanding quality ratings: {vendor.get('quality_score', 0):.1f}/5
- Excellent vendor rating: {vendor.get('rating', 0):.1f}/5
- Total successful orders: {vendor.get('successful_orders', 0)}

You are one of our most valued vendors, and your reliability, quality, and professionalism are greatly appreciated.

We look forward to a continued and growing partnership.

Best regards,
Procurement Management Team
        """
        
        self.db.log_communication(
            vendor_id,
            'appreciation',
            subject,
            body,
            'sent'
        )
    
    async def send_bulk_communication(self, vendor_ids: List[int], subject: str,
                                     body: str, comm_type: str = 'general'):
        """
        Send bulk communication to multiple vendors.
        
        Args:
            vendor_ids: List of vendor IDs
            subject: Email subject
            body: Email body
            comm_type: Type of communication
        """
        logger.info(f"Sending bulk communication to {len(vendor_ids)} vendors")
        
        for vendor_id in vendor_ids:
            self.db.log_communication(
                vendor_id,
                comm_type,
                subject,
                body,
                'sent'
            )
            await asyncio.sleep(0.1)  # Rate limiting
    
    async def manage_vendor_category(self, category: str, action: str) -> Dict:
        """
        Manage vendors in a category.
        
        Args:
            category: Vendor category
            action: Action to perform (e.g., 'enable_discount', 'suspend', 'review')
            
        Returns:
            Action result
        """
        logger.info(f"Managing category {category}: {action}")
        
        vendors = self.db.get_all_vendors()
        category_vendors = [v for v in vendors if v.get('category') == category]
        
        if action == 'enable_discount':
            message = f"Offering 5-10% discount for orders in {category}"
        elif action == 'suspend':
            message = f"Suspending new orders from {category} vendors pending review"
        elif action == 'review':
            message = f"Initiating performance review for {category} vendors"
        else:
            message = action
        
        return {
            'category': category,
            'action': action,
            'affected_vendors': len(category_vendors),
            'message': message,
            'status': 'completed'
        }
    
    def get_followup_summary(self) -> Dict:
        """Get summary of follow-up activities."""
        vendors = self.db.get_all_vendors()
        
        # Count vendors by rating
        excellent = sum(1 for v in vendors if v.get('rating', 0) >= 4.5)
        good = sum(1 for v in vendors if 3.5 <= v.get('rating', 0) < 4.5)
        needs_improvement = sum(1 for v in vendors if v.get('rating', 0) < 3.5)
        
        return {
            'total_vendors': len(vendors),
            'excellent_performers': excellent,
            'good_performers': good,
            'needs_improvement': needs_improvement,
            'next_actions': {
                'appreciate': excellent,
                'maintain': good,
                'review': needs_improvement
            }
        }
