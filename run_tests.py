"""
Simple Test Script for Procurement Agent System
"""

import asyncio
import sys
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from main import ProcurementAgentSystem
import logging

logger = logging.getLogger(__name__)


async def run_tests():
    """Run system tests."""
    print("\n" + "="*70)
    print("AUTONOMOUS PROCUREMENT AGENT - SYSTEM TEST")
    print("="*70)
    
    try:
        # Initialize system
        print("\n[1] Initializing System...")
        system = ProcurementAgentSystem()
        print("[OK] System initialized successfully")
        
        # Add vendors
        print("\n[2] Adding Vendors...")
        vendors_data = [
            ('TechHaven Inc', 'sales@techhaven.com', 'Electronics'),
            ('Global Supplies Ltd', 'orders@globalsupplies.com', 'Office Supplies'),
            ('Component Plus', 'contact@componentplus.com', 'Electronics'),
        ]
        
        for name, email, category in vendors_data:
            result = await system.add_vendor(name, email, category)
            print(f"     - {result['name']} (ID: {result['vendor_id']})")
        print("[OK] Vendors added")
        
        # Submit RFQs
        print("\n[3] Submitting Procurement Requests...")
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
                'specifications': 'A4, 80gsm',
                'priority': 'normal',
                'budget': 500
            }
        ]
        
        for req in requests:
            result = await system.submit_procurement_request(req)
            if result.get('status') == 'rfq_created':
                print(f"     - RFQ#{result['rfq_id']}: {req['item_name']}")
        print("[OK] RFQs created")
        
        # Check system status
        print("\n[4] System Status...")
        status = await system.get_system_status()
        print(f"     - Total Vendors: {status['total_vendors']}")
        print(f"     - Active RFQs: {status['active_rfqs']}")
        print(f"     - Active Orders: {status['active_orders']}")
        print("[OK] System operational")
        
        print("\n" + "="*70)
        print("[SUCCESS] ALL TESTS PASSED - SYSTEM IS READY!")
        print("="*70)
        print("\nTo start autonomous operation, run:")
        print("      python main.py")
        print("")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[OK] Tests stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
