"""
Order Agent - Execute purchase orders.
Places orders with selected vendors and manages order fulfillment.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OrderAgent:
    """Place and manage purchase orders."""
    
    def __init__(self, db, email_agent=None):
        """
        Initialize order agent.
        
        Args:
            db: Database instance
            email_agent: Email agent for sending orders
        """
        self.db = db
        self.email_agent = email_agent
        self.active_orders = {}
        self.order_confirmations = {}
    
    async def place_purchase_order(self, rfq_id: int, vendor_id: int,
                                  quotation: Dict) -> Dict:
        """
        Place a purchase order with selected vendor.
        
        Args:
            rfq_id: RFQ ID
            vendor_id: Selected vendor ID
            quotation: Selected quotation details
            
        Returns:
            Order confirmation
        """
        try:
            logger.info(f"Placing purchase order with vendor {vendor_id} for RFQ {rfq_id}")
            
            # Get vendor details
            vendor = self.db.get_all_vendors()
            vendor_data = next((v for v in vendor if v['vendor_id'] == vendor_id), None)
            
            if not vendor_data:
                logger.error(f"Vendor {vendor_id} not found")
                return {'status': 'error', 'message': 'Vendor not found'}
            
            # Calculate delivery date
            delivery_days = quotation.get('delivery_days', 7)
            expected_delivery = datetime.now() + timedelta(days=delivery_days)
            
            # Create purchase order in database
            order_id = self.db.create_purchase_order(
                vendor_id=vendor_id,
                item_name=quotation.get('item_name', 'Unknown'),
                quantity=quotation.get('quantity', 1),
                unit_price=quotation.get('unit_price', 0),
                expected_delivery=expected_delivery
            )
            
            logger.info(f"Purchase order {order_id} created")
            
            # Store order details
            self.active_orders[order_id] = {
                'rfq_id': rfq_id,
                'vendor_id': vendor_id,
                'vendor_name': vendor_data.get('name', ''),
                'vendor_email': vendor_data.get('email', ''),
                'status': 'submitted',
                'order_date': datetime.now(),
                'expected_delivery': expected_delivery,
                'item_name': quotation.get('item_name'),
                'quantity': quotation.get('quantity'),
                'unit_price': quotation.get('unit_price'),
                'total_price': quotation.get('quantity', 1) * quotation.get('unit_price', 0)
            }
            
            # Send order email
            await self._send_purchase_order_email(
                order_id, vendor_data, quotation, expected_delivery
            )
            
            # Update order status
            self.db.update_order_status(order_id, 'submitted')
            
            return {
                'status': 'order_placed',
                'order_id': order_id,
                'vendor': vendor_data.get('name'),
                'item': quotation.get('item_name'),
                'quantity': quotation.get('quantity'),
                'unit_price': quotation.get('unit_price'),
                'total_price': quotation.get('quantity', 1) * quotation.get('unit_price', 0),
                'expected_delivery': expected_delivery.isoformat(),
                'order_reference': f"PO#{order_id:06d}"
            }
            
        except Exception as e:
            logger.error(f"Error placing purchase order: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _send_purchase_order_email(self, order_id: int, vendor: Dict,
                                        quotation: Dict, expected_delivery: datetime):
        """Send purchase order email to vendor."""
        if not self.email_agent:
            logger.warning("Email agent not available")
            return
        
        subject = f"Purchase Order: PO#{order_id:06d}"
        
        body = f"""
Dear {vendor.get('name', 'Valued Vendor')},

We are pleased to confirm your quotation and place the following purchase order:

ORDER DETAILS:
--------------
PO Number: PO#{order_id:06d}
Order Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ITEM INFORMATION:
-----------------
Item: {quotation.get('item_name', 'N/A')}
Quantity: {quotation.get('quantity', 0)} units
Unit Price: ${quotation.get('unit_price', 0):.2f}
Total Price: ${quotation.get('quantity', 0) * quotation.get('unit_price', 0):.2f}

DELIVERY:
---------
Expected Delivery Date: {expected_delivery.strftime('%Y-%m-%d')}
Delivery Location: [Your Location]

PAYMENT TERMS:
--------------
{quotation.get('terms', 'Net 30')}

Please confirm receipt of this order and provide:
1. Order acknowledgment
2. Tracking information
3. Any updates regarding delivery

Contact us if you have any questions.

Best regards,
Procurement Department
        """
        
        logger.info(f"Sending purchase order email for PO#{order_id:06d}")
        
        # Log communication
        self.db.log_communication(
            vendor['vendor_id'],
            'purchase_order',
            subject,
            body,
            'sent'
        )
    
    async def monitor_orders(self, check_interval: int = 300):
        """
        Monitor purchase orders for delivery and issues.
        
        Args:
            check_interval: Seconds between checks
        """
        logger.info("Order monitoring started")
        
        while True:
            try:
                for order_id in list(self.active_orders.keys()):
                    order = self.active_orders[order_id]
                    
                    # Check if past expected delivery
                    if datetime.now() > order['expected_delivery']:
                        if order['status'] != 'delivered':
                            logger.warning(f"Order {order_id} past expected delivery")
                            await self._handle_late_delivery(order_id, order)
                    
                    # Check for delivery confirmation
                    elif order['status'] == 'submitted':
                        # Look for delivery updates (would check emails in real system)
                        pass
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring orders: {e}")
                await asyncio.sleep(check_interval)
    
    async def _handle_late_delivery(self, order_id: int, order: Dict):
        """Handle late delivery of purchase order."""
        logger.warning(f"Handling late delivery for order {order_id}")
        
        days_late = (datetime.now() - order['expected_delivery']).days
        
        if days_late > 3:
            # Send escalation email
            message = f"""
The following purchase order is {days_late} days overdue:

PO Number: PO#{order_id:06d}
Item: {order['item_name']}
Quantity: {order['quantity']}
Expected Delivery: {order['expected_delivery'].strftime('%Y-%m-%d')}

Please provide immediate update on shipment status.
            """
            
            logger.warning(f"Sending escalation for PO#{order_id:06d}")
            
            self.db.log_communication(
                order['vendor_id'],
                'delay_escalation',
                f"URGENT: Overdue Order PO#{order_id:06d}",
                message,
                'sent'
            )
    
    async def confirm_delivery(self, order_id: int, quality_rating: int = 5,
                              feedback: str = ""):
        """
        Confirm delivery of purchase order.
        
        Args:
            order_id: Order ID
            quality_rating: Quality rating (1-5)
            feedback: Delivery feedback
        """
        try:
            logger.info(f"Confirming delivery for order {order_id}")
            
            order = self.active_orders.get(order_id)
            
            # Update order status
            self.db.update_order_status(
                order_id,
                'delivered',
                quality_rating=quality_rating,
                feedback=feedback
            )
            
            # Update vendor metrics
            self.db.update_vendor_metrics(
                order['vendor_id'],
                on_time=True,
                quality_score=quality_rating / 5.0 * 5.0
            )
            
            # Update inventory
            self.db.update_inventory(
                order['item_name'],
                order['quantity']
            )
            
            # Send thank you email
            await self._send_delivery_confirmation_email(order_id, order, quality_rating)
            
            # Move order to confirmed
            if order_id in self.active_orders:
                self.active_orders[order_id]['status'] = 'delivered'
            
            logger.info(f"Delivery confirmed for order {order_id}")
            
            return {
                'status': 'delivery_confirmed',
                'order_id': order_id,
                'quality_rating': quality_rating,
                'feedback': feedback
            }
            
        except Exception as e:
            logger.error(f"Error confirming delivery: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _send_delivery_confirmation_email(self, order_id: int,
                                               order: Dict, rating: int):
        """Send delivery confirmation email to vendor."""
        if not self.email_agent:
            return
        
        subject = f"Delivery Confirmed: PO#{order_id:06d}"
        
        rating_text = "Excellent" if rating >= 4 else "Good" if rating >= 3 else "Needs Improvement"
        
        body = f"""
Dear {order['vendor_name']},

Delivery of the following purchase order has been confirmed:

PO Number: PO#{order_id:06d}
Item: {order['item_name']}
Quantity: {order['quantity']} units
Delivery Quality: {rating_text}

Thank you for your excellent service. We look forward to doing business with you again.

Best regards,
Procurement Department
        """
        
        logger.info(f"Sending delivery confirmation for PO#{order_id:06d}")
        
        self.db.log_communication(
            order['vendor_id'],
            'delivery_confirmation',
            subject,
            body,
            'sent'
        )
    
    def get_order_status(self, order_id: int) -> Dict:
        """Get current status of an order."""
        if order_id not in self.active_orders:
            return {'status': 'unknown', 'order_id': order_id}
        
        order = self.active_orders[order_id]
        days_remaining = (order['expected_delivery'] - datetime.now()).days
        
        return {
            'order_id': order_id,
            'vendor': order['vendor_name'],
            'item': order['item_name'],
            'quantity': order['quantity'],
            'status': order['status'],
            'order_date': order['order_date'].isoformat(),
            'expected_delivery': order['expected_delivery'].isoformat(),
            'days_until_delivery': max(-999, days_remaining),
            'total_price': order['total_price']
        }
    
    def get_all_orders(self) -> Dict:
        """Get summary of all active orders."""
        pending_count = sum(1 for o in self.active_orders.values() 
                          if o['status'] != 'delivered')
        delivered_count = sum(1 for o in self.active_orders.values() 
                            if o['status'] == 'delivered')
        total_value = sum(o['total_price'] for o in self.active_orders.values())
        
        return {
            'total_orders': len(self.active_orders),
            'pending': pending_count,
            'delivered': delivered_count,
            'total_value': total_value,
            'orders': self.active_orders
        }
