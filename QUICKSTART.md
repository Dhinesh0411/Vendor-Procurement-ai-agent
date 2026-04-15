# Autonomous Procurement Agent - Quick Start Guide

## 🚀 Quick Installation

```bash
# 1. Navigate to project directory
cd procurement_ai_agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your email and API credentials

# 5. Create logs directory
mkdir logs

# 6. Start the system
python main.py
```

## 📋 Project Structure

```
procurement_ai_agent/
├── main.py                      # Main orchestration system
├── requirements.txt             # Python dependencies
├── README.md                    # Full documentation
├── test_system.py               # Test and demo scripts
│
├── agents/                      # Intelligent agents
│   ├── email_agent.py          # Email monitoring (monitors incoming emails)
│   ├── extraction_agent.py      # RFQ processing (creates RFQs)
│   ├── decision_agent.py        # Vendor selection (evaluates quotations)
│   ├── order_agent.py           # Order management (places orders)
│   └── followup_agent.py        # Vendor relations (follow-ups)
│
├── database/
│   └── db.py                    # Database operations
│
├── utils/
│   └── scoring.py               # Vendor scoring algorithm
│
└── data/
    └── vendors.db               # SQLite database (auto-created)
```

## 🤖 Agent Descriptions

| Agent | Role | Key Functions |
|-------|------|---------------|
| **Email Agent** | Email Monitoring | • Monitors emails • Classifies types • Extracts data • Sends communications |
| **Extraction Agent** | Request Processing | • Processes procurement requests • Creates RFQs • Identifies vendors • Monitors responses |
| **Decision Agent** | Vendor Selection | • Scores quotations • Applies business rules • Selects best vendor • Provides reports |
| **Order Agent** | Order Management | • Places purchase orders • Tracks delivery • Confirms receipt • Updates inventory |
| **Followup Agent** | Vendor Relations | • Sends follow-ups • Rates performance • Manages communications |

## ⚙️ Configuration

Edit `.env` file:

```env
# Email Settings
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Procurement Rules
MIN_VENDOR_RATING=3.0
MAX_DELIVERY_DAYS=30

# Business Rules
AUTO_APPROVE_THRESHOLD=10000
```

## 💻 Usage Examples

### Run Full Workflow Test
```bash
python test_system.py
```

### Submit Procurement Request (Python)
```python
import asyncio
from main import ProcurementAgentSystem

async def main():
    system = ProcurementAgentSystem()
    
    result = await system.submit_procurement_request({
        'item_name': 'Microcontrollers',
        'quantity': 100,
        'priority': 'high',
        'budget': 5000
    })
    
    print(f"RFQ Created: {result['rfq_id']}")

asyncio.run(main())
```

### Add Vendor (Python)
```python
result = await system.add_vendor(
    name='TechHaven Inc',
    email='sales@techhaven.com',
    category='Electronics'
)
print(f"Vendor ID: {result['vendor_id']}")
```

### Check System Status
```python
status = await system.get_system_status()
print(f"Active RFQs: {status['active_rfqs']}")
print(f"Active Orders: {status['active_orders']}")
print(f"Total Vendors: {status['total_vendors']}")
```

## 📊 Autonomous Workflow

```
1. Email Received → Email Agent detects procurement request
                            ↓
2. RFQ Created → Extraction Agent creates RFQ
                            ↓
3. Vendors Selected → Extraction Agent identifies suitable vendors
                            ↓
4. RFQ Sent → Email Agent sends RFQ to vendors
                            ↓
5. Quotations Received → Email Agent extracts quotation data
                            ↓
6. Vendor Decision → Decision Agent evaluates and scores
                            ↓
7. Order Placed → Order Agent places PO with best vendor
                            ↓
8. Order Tracked → Order Agent monitors delivery
                            ↓
9. Delivery Confirmed → Order Agent confirms and rates
                            ↓
10. Vendor Follow-up → Follow-up Agent sends appreciation/review
```

## 🎯 Scoring Algorithm

Quotations scored on 0-100 scale:

```
Final Score = 
  (Price Score × 0.30) +           # 30% weight
  (Delivery Score × 0.25) +         # 25% weight
  (Vendor Rating Score × 0.25) +    # 25% weight
  (Quality Score × 0.20)            # 20% weight
```

**Example:**
- Price Score: 85 (competitive price)
- Delivery Score: 75 (reasonable delivery time)
- Vendor Rating: 90 (excellent vendor)
- Quality Score: 80 (good quality history)
- **Final Score: 82.5/100** ✓

## 📝 Database Tables

| Table | Purpose |
|-------|---------|
| **vendors** | Vendor information and ratings |
| **purchase_orders** | Order tracking and fulfillment |
| **rfqs** | Request for quotations |
| **quotations** | Vendor quotes for RFQs |
| **inventory** | Stock levels |
| **communication_log** | Email and communication history |

## 🔧 Troubleshooting

### Issue: Emails not being monitored
**Solution:** Check email credentials and verify IMAP is enabled

### Issue: No vendors found for procurement
**Solution:** Add more vendors or relax category filters

### Issue: Orders not being placed
**Solution:** Verify vendor emails and check business rule constraints

## 📊 Real-Time Monitoring

The system continuously monitors:
- ✓ Email inbox (5 minute intervals)
- ✓ RFQ responses (1 minute intervals)
- ✓ Order delivery (5 minute intervals)
- ✓ Vendor follow-ups (1 hour intervals)

## 🎓 Learning Resources

1. **README.md** - Complete documentation
2. **test_system.py** - Example workflows
3. **Code Comments** - Detailed inline documentation

## 📞 Key Features

✅ **Autonomous Operation** - Runs 24/7 without intervention
✅ **Email Integration** - Seamless email-based workflow
✅ **Intelligent Scoring** - Multi-criteria vendor evaluation
✅ **Real-Time Tracking** - Live monitoring of RFQs and orders
✅ **Database Storage** - Complete audit trail
✅ **Performance Analytics** - Vendor metrics and statistics
✅ **Relationship Management** - Vendor follow-ups and ratings

## ⭐ Next Steps

1. ✓ Install dependencies: `pip install -r requirements.txt`
2. ✓ Configure email: Edit `.env` file
3. ✓ Test system: `python test_system.py`
4. ✓ Start system: `python main.py`
5. ✓ Monitor logs in `logs/procurement_agent.log`

## 📝 Notes

- System runs asynchronously - all agents operate concurrently
- Database is automatically created on first run
- All communications are logged for audit trail
- Configure business rules in `.env` file
- Test workflows available in `test_system.py`

---

**Ready to go!** The system is fully autonomous and production-ready. 🚀
