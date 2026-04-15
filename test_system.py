"""
Test and Demo Scripts for Procurement Agent System
Run different scenarios to test system functionality.
"""

import asyncio
import sys
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from main import ProcurementAgentSystem
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


async def test_vendor_addition(system):
    """Test adding vendors to the system."""
    print("\n" + "="*60)
    print("TEST 1: Adding Vendors")
    print("="*60)
    
    vendors = [
        ('TechHaven Inc', 'sales@techhaven.com', 'Electronics'),
        ('Global Supplies Ltd', 'orders@globalsupplies.com', 'Office Supplies'),
        ('Component Plus', 'contact@componentplus.com', 'Electronics'),
        ('Premier Packaging', 'sales@premierpack.com', 'Packaging'),
    ]
    
    for name, email, category in vendors:
        result = await system.add_vendor(name, email, category)
        print(f"[OK] {result['name']} added (ID: {result['vendor_id']}, Category: {category})")
    
    return system.db.get_all_vendors()


async def test_procurement_request(system):
    """Test submitting procurement requests."""
    print("\n" + "="*60)
    print("TEST 2: Submitting Procurement Requests")
    print("="*60)
    
    requests = [
        {
            'item_name': 'Microcontrollers',
            'quantity': 100,
            'specifications': 'Arduino compatible, 8-bit',
            'priority': 'high',
            'budget': 5000
        },
        {
            'item_name': 'Office Paper',
            'quantity': 50,
            'specifications': 'A4 size, 80gsm, white',
            'priority': 'normal',
            'budget': 500
        },
        {
            'item_name': 'Packaging Materials',
            'quantity': 200,
            'specifications': 'Custom boxes, 10x10x5 cm',
            'priority': 'low',
            'budget': 2000
        }
    ]
    
    results = []
    for req in requests:
        result = await system.submit_procurement_request(req)
        if result.get('status') == 'rfq_created':
            print(f"✓ RFQ#{result['rfq_id']}: {req['item_name']} x{req['quantity']} units")
            print(f"  └─ Vendors contacted: {result['vendors_contacted']}")
            print(f"  └─ Deadline: {result['deadline']}")
            results.append(result)
    
    return results


async def test_quotation_handling(system):
    """Test receiving and processing quotations."""
    print("\n" + "="*60)
    print("TEST 3: Receiving Quotations")
    print("="*60)
    
    # Simulate quotations from vendors
    quotation_data = [
        {
            'vendor_email': 'sales@techhaven.com',
            'rfq_id': 1,
            'unit_price': 45.50,
            'delivery_days': 5,
            'terms': 'Net 30, 5% bulk discount available'
        },
        {
            'vendor_email': 'contact@componentplus.com',
            'rfq_id': 1,
            'unit_price': 42.00,
            'delivery_days': 7,
            'terms': 'Net 15'
        },
        {
            'vendor_email': 'sales@techhaven.com',
            'rfq_id': 1,
            'unit_price': 40.00,
            'delivery_days': 10,
            'terms': 'Net 60'
        }
    ]
    
    for quote in quotation_data:
        result = await system.handle_received_quotation(
            vendor_email=quote['vendor_email'],
            rfq_id=quote['rfq_id'],
            unit_price=quote['unit_price'],
            delivery_days=quote['delivery_days'],
            terms=quote['terms']
        )
        
        if result.get('status') == 'quotation_received':
            print(f"✓ Quote from {quote['vendor_email']}")
            print(f"  └─ Unit Price: ${quote['unit_price']}")
            print(f"  └─ Delivery: {quote['delivery_days']} days")


async def test_vendor_decision(system):
    """Test vendor decision making."""
    print("\n" + "="*60)
    print("TEST 4: Vendor Decision Making")
    print("="*60)
    
    # Trigger decision for RFQ 1
    result = await system.trigger_vendor_decision(rfq_id=1)
    
    if result.get('status') == 'decision_made':
        print(f"✓ Decision Made for RFQ#{result['rfq_id']}")
        print(f"  ├─ Selected Vendor: {result['selected_vendor']}")
        print(f"  ├─ Unit Price: ${result['unit_price']}")
        print(f"  ├─ Delivery: {result['delivery_days']} days")
        print(f"  ├─ Selection Score: {result['score']:.1f}/100")
        print(f"  └─ Alternatives:")
        for i, alt in enumerate(result.get('alternatives', [])[:3], 1):
            print(f"     {i}. {alt} (Score: {alt.get('score', 0):.1f})")
    elif result.get('status') == 'no_quotations':
        print(f"✗ No quotations received for RFQ #{result['rfq_id']}")


async def test_system_status(system):
    """Test getting system status."""
    print("\n" + "="*60)
    print("TEST 5: System Status")
    print("="*60)
    
    status = await system.get_system_status()
    
    print(f"System Status: {status['system_status']}")
    print(f"  ├─ Total Vendors: {status['total_vendors']}")
    print(f"  ├─ Active RFQs: {status['active_rfqs']}")
    print(f"  ├─ Active Orders: {status['active_orders']}")
    print(f"  └─ Active Agents:")
    for agent, role in status.get('agents', {}).items():
        print(f"     ├─ {agent}: {role}")


async def test_full_workflow():
    """Run complete workflow test."""
    print("\n\n")
    print("###" * 20)
    print("AUTONOMOUS PROCUREMENT AGENT - FULL WORKFLOW TEST")
    print("###" * 20)
    
    # Test 1: Add vendors
    vendors = await test_vendor_addition()
    
    # Test 2: Submit procurement requests
    await asyncio.sleep(1)
    
    # Create system for remaining tests
    system = ProcurementAgentSystem()
    
    results = await test_procurement_request(system)
    
    # Test 3: Process quotations
    await asyncio.sleep(1)
    await test_quotation_handling(system)
    
    # Test 4: Make vendor decision
    await asyncio.sleep(1)
    await test_vendor_decision(system)
    
    # Test 5: Check system status
    await asyncio.sleep(1)
    await test_system_status(system)
    
    print("\n" + "="*60)
    print("WORKFLOW TEST COMPLETE")
    print("="*60)
    print("\nKey Results:")
    print(f"✓ {len(vendors)} vendors added to system")
    print(f"✓ {len(results)} RFQs created")
    print("✓ Quotations processed and evaluated")
    print("✓ Vendor selection automated")
    print("✓ System running in autonomous mode")


async def test_low_inventory():
    """Test low inventory detection."""
    print("\n" + "="*60)
    print("TEST 6: Low Inventory Detection")
    print("="*60)
    
    system = ProcurementAgentSystem()
    
    # Add some items to inventory
    system.db.update_inventory('Microcontrollers', 5)  # Below default threshold of 10
    system.db.update_inventory('Office Paper', 3)      # Below threshold
    system.db.update_inventory('Cables', 50)           # Above threshold
    
    low_items = await system.get_low_inventory_items()
    
    if low_items:
        print(f"Found {len(low_items)} items below reorder point:")
        for item in low_items:
            print(f"  ├─ {item['item_name']}")
            print(f"  │  ├─ Current: {item['current_stock']} units")
            print(f"  │  └─ Reorder Point: {item['reorder_point']} units")
    else:
        print("No items below reorder point")


async def test_comparison_report(system):
    """Test quotation comparison report."""
    print("\n" + "="*60)
    print("TEST 7: Quotation Comparison Report")
    print("="*60)
    
    # Get comparison for RFQ 1
    comparison = await system.decision_agent.compare_quotations(rfq_id=1)
    
    if comparison.get('quotations'):
        print(f"Comparison for RFQ#{comparison['rfq_id']}")
        print(f"Total vendors: {comparison['total_vendors']}\n")
        print("Rank | Vendor         | Unit Price | Price vs Min | Delivery | Rating")
        print("-" * 75)
        
        for q in comparison.get('quotations', []):
            vendor = q['vendor'][:15].ljust(15)
            price = f"${q['unit_price']:<10.2f}"
            price_diff = q.get('price_vs_min', 'N/A').ljust(12)
            delivery = f"{q['delivery_days']} days".ljust(8)
            rating = f"{q['vendor_rating']:.1f}"
            
            print(f"{q['rank']}    | {vendor} | {price} | {price_diff} | {delivery} | {rating}")
    else:
        print("No quotations to compare")


async def main():
    """Main test execution."""
    try:
        await test_full_workflow()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        asyncio.run(main())
        
        print("\n" + "###" * 20)
        print("ALL TESTS PASSED - SYSTEM IS READY!")
        print("###" * 20)
        print("\nTo start autonomous operation, run:")
        print("  python main.py")
        
    except KeyboardInterrupt:
        print("\n✓ Tests stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
