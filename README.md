# Autonomous Procurement and Vendor Management System

A complete AI-powered autonomous procurement system that manages vendor relationships, RFQs, purchase orders, and supplier ratings with intelligent agents.

## Features

### 🤖 Intelligent Agents

1. **Email Agent** - Autonomous email monitoring
   - Monitors incoming emails for procurement requests
   - Classifies email types (RFQ requests, quotations, delivery updates, complaints)
   - Extracts structured data from unstructured emails
   - Sends automated communications

2. **Extraction Agent** - Procurement request processing
   - Processes procurement requests from emails
   - Creates RFQs (Request for Quotations)
   - Identifies suitable vendors based on historical data
   - Sends RFQs to multiple vendors
   - Monitors RFQ responses and deadlines

3. **Decision Agent** - Intelligent vendor selection
   - Evaluates and scores quotations using multi-criteria analysis
   - Considers price, delivery time, vendor rating, and quality
   - Applies business rules and constraints
   - Provides detailed comparison reports
   - Selects best vendor automatically

4. **Order Agent** - Purchase order management
   - Places purchase orders with selected vendors
   - Tracks order status and delivery
   - Monitors for late deliveries
   - Confirms delivery and quality ratings
   - Updates inventory

5. **Follow-up Agent** - Vendor relationship management
   - Monitors vendor performance
   - Sends follow-up emails for pending orders
   - Provides performance reviews for underperforming vendors
   - Recognizes high-performing vendors
   - Manages bulk communications

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│       Main Orchestration System (main.py)           │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────┬─────────┐
        │            │            │          │         │
    ┌───▼──┐    ┌─────▼──┐  ┌──────▼──┐ ┌──▼────┐  ┌─▼──────┐
    │Email │    │Extract │  │Decision │ │Order  │  │Followup│
    │Agent │    │ Agent  │  │ Agent   │ │Agent  │  │ Agent  │
    └──────┘    └────────┘  └─────────┘ └───────┘  └────────┘
        │            │            │          │         │
        └────────────┼────────────┼──────────┼─────────┘
                     │
        ┌────────────▼────────────┐
        │  Database (vendors.db)  │
        │  - Vendors              │
        │  - RFQs                 │
        │  - Quotations           │
        │  - Orders               │
        │  - Communications       │
        │  - Inventory            │
        └─────────────────────────┘
```

## Installation

1. **Clone the repository**
   ```bash
   cd procurement_ai_agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Create logs directory**
   ```bash
   mkdir logs
   ```

## Usage

### Starting the System

```bash
python main.py
```

This starts all agents in autonomous mode:
- Email monitoring (every 5 minutes)
- RFQ response monitoring (every 1 minute)
- Order delivery tracking (every 5 minutes)
- Vendor follow-ups (every 1 hour)

### Submitting Procurement Request

```python
import asyncio
from main import ProcurementAgentSystem

async def main():
    system = ProcurementAgentSystem()
    
    result = await system.submit_procurement_request({
        'item_name': 'Microcontrollers',
        'quantity': 100,
        'specifications': 'Arduino compatible',
        'priority': 'high',
        'budget': 5000
    })
    
    print(f"RFQ Created: {result['rfq_id']}")

asyncio.run(main())
```

### Adding Vendors

```python
async def main():
    system = ProcurementAgentSystem()
    
    result = await system.add_vendor(
        name='TechHaven Inc',
        email='sales@techhaven.com',
        category='Electronics'
    )
    
    print(f"Vendor Added: {result['vendor_id']}")

asyncio.run(main())
```

### Checking System Status

```python
async def main():
    system = ProcurementAgentSystem()
    status = await system.get_system_status()
    
    print(f"Active RFQs: {status['active_rfqs']}")
    print(f"Active Orders: {status['active_orders']}")
    print(f"Total Vendors: {status['total_vendors']}")

asyncio.run(main())
```

## Autonomous Workflow

### 1. Procurement Request Received
- Email Agent detects procurement email
- Extracts item name, quantity, specifications
- Creates RFQ in database

### 2. Vendor Selection & RFQ Distribution
- Extraction Agent identifies suitable vendors
- Sends RFQ emails to selected vendors
- Monitors for responses

### 3. Quotation Analysis
- Email Agent receives quotations from vendors
- Extracts price, delivery time, terms
- Stores quotations in database

### 4. Intelligent Decision Making
- Decision Agent evaluates all quotations
- Scores based on: price, delivery time, vendor rating, quality
- Selects best vendor automatically

### 5. Purchase Order Creation
- Order Agent creates purchase order
- Sends PO email to selected vendor
- Updates database and inventory

### 6. Order Fulfillment Tracking
- Order Agent monitors delivery status
- Checks for delivery delays
- Confirms receipt and quality

### 7. Vendor Relationship Management
- Follow-up Agent sends follow-up emails
- Rates vendor performance
- Prepares appreciation or review emails

## Scoring Algorithm

Quotations are scored using a weighted multi-criteria approach:

```
Score = (Price × 0.30) + (Delivery Time × 0.25) + (Vendor Rating × 0.25) + (Quality × 0.20)

Each criterion is scored 0-100:
- Price Score: Lower price = higher score
- Delivery Time Score: Faster delivery = higher score
- Vendor Rating Score: Converts 0-5 rating to 0-100
- Quality Score: Based on historical quality ratings
```

## Database Schema

### Vendors Table
- vendor_id, name, email, category
- rating, on_time_delivery_rate, quality_score
- total_orders, successful_orders, status

### Purchase Orders Table
- order_id, vendor_id, item_name, quantity, unit_price
- status, order_date, expected_delivery_date, actual_delivery_date
- quality_rating, feedback

### RFQs Table
- rfq_id, item_name, quantity, specifications
- deadline, status, responses_count, created_at

### Quotations Table
- quote_id, rfq_id, vendor_id, unit_price
- delivery_days, terms, score, selected

### Inventory Table
- item_id, item_name, current_stock
- min_threshold, max_threshold, reorder_point

### Communication Log Table
- log_id, vendor_id, message_type, subject
- content, status, sent_at, response_received

## Configuration

Edit `.env` file to configure:

```env
# Email settings
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Procurement settings
MIN_VENDOR_RATING=3.0
MAX_DELIVERY_DAYS=30

# Business rules
AUTO_APPROVE_THRESHOLD=10000
```

## Advanced Features

### Real-Time Monitoring
- Live tracking of RFQ status
- Order delivery monitoring
- Vendor performance real-time updates

### Business Rules Engine
- Automatic approval for qualifying orders
- Maximum price constraints
- Preferred vendor prioritization
- Delivery time requirements

### Performance Analytics
- Vendor performance metrics
- Order fulfillment rates
- Cost analysis
- Delivery performance

### Escalation Handling
- Late delivery escalation
- Quality issue management
- Vendor performance reviews
- Low stock alerts

## API Reference

### Core Methods

```python
# Procurement requests
await system.submit_procurement_request(request_data: Dict) -> Dict
await system.handle_received_quotation(...) -> Dict
await system.trigger_vendor_decision(rfq_id: int) -> Dict

# Vendor management
await system.add_vendor(name: str, email: str, category: str) -> Dict

# Monitoring
await system.get_system_status() -> Dict
await system.monitor_rfq(rfq_id: int) -> Dict
await system.get_low_inventory_items() -> List[Dict]

# System control
await system.start()
await system.stop()
```

## Logging

Logs are saved to `logs/procurement_agent.log` and also printed to console.

Log levels:
- INFO: General agent operations
- WARNING: Delivery delays, performance issues
- ERROR: System errors requiring attention
- DEBUG: Detailed debugging information

## Future Enhancements

- [ ] Integration with supplier ERP systems
- [ ] Machine learning for vendor recommendation
- [ ] Advanced demand forecasting
- [ ] Multi-currency support
- [ ] Integration with financial systems
- [ ] Compliance and audit tracking
- [ ] Mobile notifications
- [ ] Web dashboard for monitoring

## Troubleshooting

### Email not being monitored
- Check email credentials in .env
- Verify IMAP is enabled in email settings
- Check firewall/network settings

### No vendors matching procurement request
- Add more vendors to the database
- Relax category filters
- Review vendor rating thresholds

### Orders not being placed
- Verify email configuration
- Check vendor email addresses
- Review business rule constraints

## License

MIT License

## Support

For issues, questions, or suggestions, please refer to the documentation or contact the development team.

---

**Status**: Active Autonomous Operation
**Last Updated**: 2026-04-14
**Version**: 1.0.0
