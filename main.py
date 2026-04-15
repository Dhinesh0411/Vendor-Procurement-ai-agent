"""
Main Autonomous Procurement Agent System
Orchestrates all procurement agents in an autonomous workflow.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup paths - get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Load environment variables from .env file in the same directory
env_file = SCRIPT_DIR / '.env'
load_dotenv(dotenv_path=env_file)

# Ensure logs and data directories exist
logs_dir = SCRIPT_DIR / 'logs'
data_dir = SCRIPT_DIR / 'data'
logs_dir.mkdir(exist_ok=True)
data_dir.mkdir(exist_ok=True)

# Configure logging with absolute path
log_file = logs_dir / 'procurement_agent.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import all agents - now paths are set up correctly
from database.db import ProcurementDB
from agents.email_agent import EmailAgent
from agents.extraction_agent import ExtractionAgent
from agents.decision_agent import DecisionAgent
from agents.order_agent import OrderAgent
from agents.followup_agent import FollowupAgent


class ProcurementAgentSystem:
    """Main orchestration system for autonomous procurement."""
    
    def __init__(self):
        """Initialize all agents and database."""
        logger.info("=" * 60)
        logger.info("Initializing Autonomous Procurement Agent System")
        logger.info("=" * 60)
        
        # Initialize database with absolute path
        db_path = SCRIPT_DIR / 'data' / 'vendors.db'
        self.db = ProcurementDB(str(db_path))
        logger.info("[OK] Database initialized")
        
        # Email configuration
        email_config = {
            'imap_server': os.getenv('EMAIL_IMAP_SERVER', 'imap.gmail.com'),
            'smtp_server': os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
            'email_address': os.getenv('EMAIL_ADDRESS'),
            'email_password': os.getenv('EMAIL_PASSWORD'),
        }
        
        # Initialize agents
        self.email_agent = EmailAgent(self.db, email_config)
        logger.info("[OK] Email Agent initialized")
        
        self.extraction_agent = ExtractionAgent(self.db, self.email_agent)
        logger.info("[OK] Extraction Agent initialized")
        
        self.order_agent = OrderAgent(self.db, self.email_agent)
        logger.info("[OK] Order Agent initialized")
        
        self.decision_agent = DecisionAgent(self.db, self.order_agent)
        logger.info("[OK] Decision Agent initialized")
        
        self.followup_agent = FollowupAgent(self.db, self.email_agent)
        logger.info("[OK] Follow-up Agent initialized")
        
        self.running = False
        self.pending_rfqs = {}
        self.decision_queue = []
    
    async def start(self):
        """Start the autonomous procurement system."""
        self.running = True
        logger.info("\n✓ Autonomous Procurement Agent System STARTED")
        logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 60)
        
        # Create tasks for all agents
        tasks = [
            asyncio.create_task(self.email_agent.start_monitoring(check_interval=300)),
            asyncio.create_task(self.extraction_agent.monitor_rfq_responses(check_interval=60)),
            asyncio.create_task(self.order_agent.monitor_orders(check_interval=300)),
            asyncio.create_task(self.followup_agent.process_pending_followups(check_interval=3600)),
            asyncio.create_task(self._main_orchestration_loop()),
        ]
        
        try:
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("\nShutdown signal received")
            await self.stop()
        except Exception as e:
            logger.error(f"Error in agent system: {e}")
            await self.stop()
    
    async def _main_orchestration_loop(self):
        """Main orchestration loop coordinating agents."""
        logger.info("Main orchestration loop started")
        
        while self.running:
            try:
                # Check for pending decisions
                await self._process_pending_decisions()
                
                # Monitor system health
                await self._monitor_system_health()
                
                # Check for manually submitted procurement requests
                await self._check_procurement_requests()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(30)
    
    async def _process_pending_decisions(self):
        """Process pending vendor decisions."""
        # This would be populated by the extraction agent
        # when RFQ deadline approaches or enough quotes received
        pass
    
    async def _monitor_system_health(self):
        """Monitor overall system health and performance."""
        # Log agent status
        email_status = "running" if self.email_agent.running else "stopped"
        rfqs_active = len(self.extraction_agent.active_rfqs)
        orders_active = len(self.order_agent.active_orders)
        
        logger.debug(f"System Health - Email: {email_status}, Active RFQs: {rfqs_active}, Active Orders: {orders_active}")
    
    async def _check_procurement_requests(self):
        """Check for new procurement requests."""
        # In production, would check for:
        # - REST API requests
        # - Database procurement requests queue
        # - Email procurement requests
        pass
    
    async def submit_procurement_request(self, request_data: Dict) -> Dict:
        """
        Submit a procurement request to the system.
        
        Args:
            request_data: Procurement request with item_name, quantity, etc.
            
        Returns:
            Processing status
        """
        logger.info(f"Procurement request received: {request_data.get('item_name')}")
        
        try:
            # Process through extraction agent
            result = await self.extraction_agent.process_procurement_request(request_data)
            return result
            
        except Exception as e:
            logger.error(f"Error processing procurement request: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def add_vendor(self, name: str, email: str, category: str) -> Dict:
        """Add a new vendor to the system."""
        logger.info(f"Adding vendor: {name}")
        
        vendor_id = self.db.add_vendor(name, email, category)
        
        return {
            'status': 'vendor_added',
            'vendor_id': vendor_id,
            'name': name,
            'email': email,
            'category': category
        }
    
    async def monitor_rfq(self, rfq_id: int) -> Dict:
        """Get status of an RFQ."""
        return self.extraction_agent.get_rfq_status(rfq_id)
    
    async def get_system_status(self) -> Dict:
        """Get overall system status."""
        vendors = self.db.get_all_vendors()
        
        return {
            'system_status': 'running' if self.running else 'stopped',
            'start_time': datetime.now().isoformat(),
            'email_agent': 'active' if self.email_agent.running else 'inactive',
            'total_vendors': len(vendors),
            'active_rfqs': len(self.extraction_agent.active_rfqs),
            'active_orders': len(self.order_agent.active_orders),
            'agents': {
                'email_agent': 'monitoring',
                'extraction_agent': 'processing RFQs',
                'decision_agent': 'evaluating quotations',
                'order_agent': 'managing orders',
                'followup_agent': 'vendor relations'
            }
        }
    
    async def get_low_inventory_items(self) -> List[Dict]:
        """Get items below reorder point."""
        return self.db.get_low_stock_items()
    
    async def handle_received_quotation(self, vendor_email: str, rfq_id: int,
                                       unit_price: float, delivery_days: int,
                                       terms: str) -> Dict:
        """
        Handle manually received quotation email.
        
        Args:
            vendor_email: Vendor email address
            rfq_id: RFQ ID
            unit_price: Unit price in quotation
            delivery_days: Delivery time
            terms: Payment terms
            
        Returns:
            Processing result
        """
        logger.info(f"Handling quotation from {vendor_email} for RFQ {rfq_id}")
        
        try:
            # Get vendor ID
            vendor_name = vendor_email.split('@')[0]
            vendor_id = self.db.get_vendor_by_name(vendor_name)
            
            if not vendor_id:
                return {'status': 'error', 'message': f'Vendor {vendor_email} not found'}
            
            # Add quotation
            quote_id = self.db.add_quotation(
                rfq_id, vendor_id, unit_price, delivery_days, terms
            )
            
            logger.info(f"Quotation {quote_id} added")
            
            return {
                'status': 'quotation_received',
                'quote_id': quote_id,
                'rfq_id': rfq_id,
                'vendor': vendor_name,
                'unit_price': unit_price,
                'delivery_days': delivery_days
            }
            
        except Exception as e:
            logger.error(f"Error handling quotation: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def trigger_vendor_decision(self, rfq_id: int) -> Dict:
        """
        Manually trigger decision for an RFQ.
        
        Args:
            rfq_id: RFQ ID
            
        Returns:
            Decision result
        """
        logger.info(f"Manual decision trigger for RFQ {rfq_id}")
        
        return await self.decision_agent.evaluate_quotations(rfq_id)
    
    async def stop(self):
        """Stop the autonomous system."""
        logger.info("\n" + "=" * 60)
        logger.info("Shutting down Autonomous Procurement Agent System")
        logger.info("=" * 60)
        
        self.running = False
        self.email_agent.stop_monitoring()
        
        # Get final statistics
        status = await self.get_system_status()
        
        logger.info(f"Final System Status:")
        logger.info(f"  - Total Vendors: {status['total_vendors']}")
        logger.info(f"  - Active RFQs: {status['active_rfqs']}")
        logger.info(f"  - Active Orders: {status['active_orders']}")
        
        logger.info("System shutdown complete")


async def demo_workflow():
    """Demo workflow showing the system in action."""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO: Autonomous Procurement Workflow")
    logger.info("=" * 60)
    
    system = ProcurementAgentSystem()
    
    # Add sample vendors
    logger.info("\n### Adding Sample Vendors ###")
    vendors = [
        ('TechHaven Inc', 'sales@techhaven.com', 'Electronics'),
        ('Global Supplies Ltd', 'orders@globalsupplies.com', 'Office Supplies'),
        ('Component Plus', 'contact@componentplus.com', 'Electronics'),
    ]
    
    for name, email, category in vendors:
        result = await system.add_vendor(name, email, category)
        logger.info(f"[OK] {result['name']} added (ID: {result['vendor_id']})")
    
    # Submit procurement requests
    logger.info("\n### Submitting Procurement Requests ###")
    requests = [
        {
            'item_name': 'Microcontrollers',
            'quantity': 100,
            'specifications': 'Arduino compatible',
            'priority': 'high',
            'budget': 5000
        },
        {
            'item_name': 'Office Paper',
            'quantity': 50,
            'specifications': 'A4 size, 80gsm',
            'priority': 'normal',
            'budget': 500
        }
    ]
    
    for req in requests:
        result = await system.submit_procurement_request(req)
        logger.info(f"[OK] {req['item_name']}: {result.get('status')} (RFQ#{result.get('rfq_id')})")
    
    # Show system status
    logger.info("\n### System Status ###")
    status = await system.get_system_status()
    logger.info(f"[OK] Running Agents: {len([a for a in status['agents']])}")
    logger.info(f"[OK] Active RFQs: {status['active_rfqs']}")
    logger.info(f"[OK] Total Vendors: {status['total_vendors']}")
    
    logger.info("\n### Demo Complete - System Ready for Autonomous Operation ###")
    
    # Start the system
    logger.info("\nStarting autonomous operation (Press Ctrl+C to stop)...")
    await system.start()


if __name__ == '__main__':
    try:
        print("\n" + "="*60)
        print("AUTONOMOUS PROCUREMENT AGENT SYSTEM")
        print("="*60)
        print("\nStarting system (Check logs/procurement_agent.log for details)")
        print("Press Ctrl+C to stop...\n")
        
        # Run demo async
        asyncio.run(demo_workflow())
        
    except KeyboardInterrupt:
        print("\n[OK] System stopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
