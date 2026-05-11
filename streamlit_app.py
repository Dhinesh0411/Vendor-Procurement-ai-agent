import asyncio
import random
import sqlite3
from pathlib import Path

import streamlit as st

from main import ProcurementAgentSystem

SCRIPT_DIR = Path(__file__).parent.resolve()
LOG_FILE = SCRIPT_DIR / "logs" / "procurement_agent.log"
DB_PATH = SCRIPT_DIR / "data" / "vendors.db"


def run_async(coroutine):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    else:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coroutine)
        finally:
            new_loop.close()
            asyncio.set_event_loop(loop)


def get_system():
    if "procurement_system" not in st.session_state:
        st.session_state.procurement_system = ProcurementAgentSystem()
    return st.session_state.procurement_system


def tail_log(filepath: Path, lines: int = 20):
    if not filepath.exists():
        return []

    with filepath.open("r", encoding="utf-8", errors="ignore") as f:
        data = f.read().splitlines()

    return data[-lines:]


def get_recent_communications(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM communication_log ORDER BY sent_at DESC LIMIT ?",
        (limit,),
    )

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def simulate_all_vendor_quotes(system, rfq):
    all_vendors = system.db.get_all_vendors()
    existing_quotes = system.db.get_rfq_quotations(rfq['rfq_id'])
    existing_vendor_ids = {quote['vendor_id'] for quote in existing_quotes}

    for vendor in all_vendors:
        if vendor['vendor_id'] in existing_vendor_ids:
            continue

        unit_price = round(random.uniform(80.0, 120.0) * (1 + random.uniform(-0.05, 0.05)), 2)
        delivery_days = random.randint(3, 14)
        terms = f"Auto-generated quote for {rfq['item_name']}"

        system.db.add_quotation(
            rfq_id=rfq['rfq_id'],
            vendor_id=vendor['vendor_id'],
            unit_price=unit_price,
            delivery_days=delivery_days,
            terms=terms
        )

    quotations = system.db.get_rfq_quotations(rfq['rfq_id'])
    if len(quotations) >= 3:
        run_async(system.decision_agent.evaluate_quotations(rfq['rfq_id']))


def main():
    st.set_page_config(page_title="Procurement AI Dashboard", layout="wide")
    st.title("Procurement AI Dashboard")

    system = get_system()

    st.sidebar.header("Quick Actions")

    with st.sidebar.expander("Add New Vendor", expanded=True):
        vendor_name = st.text_input("Vendor Name", key="vendor_name")
        vendor_email = st.text_input("Vendor Email", key="vendor_email")
        vendor_category = st.text_input("Vendor Category", key="vendor_category")

        if st.button("Add Vendor"):
            if vendor_name and vendor_email:
                result = run_async(system.add_vendor(vendor_name, vendor_email, vendor_category))
                st.success(f"Vendor added: {result.get('name')} (ID: {result.get('vendor_id')})")
            else:
                st.error("Vendor name and email are required.")

    with st.sidebar.expander("Create Procurement Request", expanded=False):
        item_name = st.text_input("Item Name", key="item_name")
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1, key="quantity")
        specifications = st.text_area("Specifications", key="specifications")
        priority = st.selectbox("Priority", ["normal", "high", "urgent", "low"], key="priority")
        budget = st.number_input("Budget", min_value=0.0, value=0.0, format="%.2f", key="budget")

        if st.button("Submit Procurement Request"):
            if item_name:
                request_data = {
                    "item_name": item_name,
                    "quantity": int(quantity),
                    "specifications": specifications,
                    "priority": priority,
                    "budget": float(budget),
                }
                result = run_async(system.submit_procurement_request(request_data))
                if result.get("status") == "error":
                    st.error(result.get("message"))
                else:
                    st.success(f"Procurement request created: {result.get('status')}")
                    st.json(result)
            else:
                st.error("Item name is required.")

    with st.sidebar.expander("Quick RFQ: 100 Computers", expanded=False):
        st.markdown("**Create a fast test request for 100 computers across all vendors.**")
        if st.button("Create 100-Computer RFQ"):
            demo_request = {
                "item_name": "Computer",
                "quantity": 100,
                "specifications": "Requesting 100 office desktop computers with standard warranty and shipping.",
                "priority": "normal",
                "budget": 100000.0
            }
            result = run_async(system.submit_procurement_request(demo_request))
            if result.get("status") == "rfq_created":
                st.success(f"✅ RFQ #{result['rfq_id']} created for 100 computers.")
                st.info(f"📧 Sent request to {result['vendors_contacted']} vendors.")
            else:
                st.error(f"Failed to create RFQ: {result.get('message', result)}")

    # Add Demo Tender Section
    with st.sidebar.expander("🚀 Demo: Send Tender to Vendors", expanded=False):
        st.markdown("**Create a demo tender and see how the AI processes vendor responses.**")

        demo_item = st.selectbox(
            "Select Demo Item",
            ["Laptop Computers", "Office Chairs", "Printer Paper", "Network Cables", "Coffee Machines"],
            key="demo_item"
        )

        demo_quantity = st.slider("Quantity", min_value=1, max_value=100, value=10, key="demo_quantity")

        if st.button("🚀 Send Demo Tender", type="primary"):
            # Create demo procurement request
            demo_request = {
                "item_name": demo_item,
                "quantity": demo_quantity,
                "specifications": f"High-quality {demo_item.lower()} for office use. Must meet industry standards.",
                "priority": "normal",
                "budget": 5000.0
            }

            result = run_async(system.submit_procurement_request(demo_request))

            if result.get("status") == "rfq_created":
                st.success(f"✅ Demo tender sent! RFQ #{result['rfq_id']} created for {demo_item}")
                st.info(f"📧 System sent RFQ to {result['vendors_contacted']} vendors. Check the 'Active Tenders' section below to see responses.")
                st.balloons()
            else:
                st.error(f"Failed to create demo tender: {result}")

    st.sidebar.markdown("---")
    st.sidebar.write("Use the controls to add vendors, create requests, and inspect current system state.")

    st.header("System Summary")
    try:
        status = run_async(system.get_system_status())
    except Exception as exc:
        st.error(f"Unable to get system status: {exc}")
        status = {
            "system_status": "unknown",
            "email_agent": "unknown",
            "total_vendors": 0,
            "active_rfqs": 0,
            "active_orders": 0,
        }

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("System State", status.get("system_status", "unknown"))
    col2.metric("Email Agent", status.get("email_agent", "unknown"))
    col3.metric("Vendors", status.get("total_vendors", 0))
    col4.metric("Active RFQs", status.get("active_rfqs", 0))

    st.subheader("Agent Status")
    st.json(status.get("agents", {}))

    vendors = system.db.get_all_vendors()
    st.subheader("Vendor Directory")
    if vendors:
        st.dataframe(vendors)
    else:
        st.info("No vendors in the database yet.")

    low_stock = system.db.get_low_stock_items()
    st.subheader("Low Inventory Items")
    if low_stock:
        st.dataframe(low_stock)
    else:
        st.info("No low inventory items found.")

    st.subheader("Recent Communication Log")
    communications = get_recent_communications(limit=12)
    if communications:
        st.dataframe(communications)
    else:
        st.info("No communications logged yet.")

    # Add Active RFQs and Quotations Section
    st.header("Active Tenders (RFQs) & Vendor Responses")

    # Get active RFQs from the system
    try:
        # Get all RFQs from database
        rfqs = system.db.get_all_rfqs()
        if rfqs:
            st.subheader("Current Active Tenders")

            # Show chosen vendor summary for all active RFQs
            chosen_summary = []
            for rfq in rfqs:
                quotations = system.db.get_rfq_quotations(rfq['rfq_id'])
                selected_quotes = [q for q in quotations if q.get('selected', False)]
                if selected_quotes:
                    selected = selected_quotes[0]
                    chosen_summary.append({
                        'RFQ #': rfq['rfq_id'],
                        'Item': rfq['item_name'],
                        'Selected Vendor': selected.get('vendor_name', 'Unknown'),
                        'Price': f"${selected.get('unit_price', 0):.2f}",
                        'Score': f"{selected.get('score', 0):.1f}",
                        'Delivery Days': selected.get('delivery_days', 'N/A')
                    })

            if chosen_summary:
                st.subheader("Chosen Vendor Summary")
                st.dataframe(chosen_summary, use_container_width=True)
            else:
                st.info("No chosen vendors yet. Select quotes by receiving quotations or simulating vendor responses.")

            # Create tabs for each RFQ
            rfq_tabs = st.tabs([f"RFQ #{rfq['rfq_id']} - {rfq['item_name']}" for rfq in rfqs[:5]])  # Show latest 5

            for i, (tab, rfq) in enumerate(zip(rfq_tabs, rfqs[:5])):
                with tab:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Item", rfq['item_name'])
                    col2.metric("Quantity", rfq['quantity'])
                    col3.metric("Deadline", rfq.get('deadline', 'N/A'))

                    # Get quotations for this RFQ
                    quotations = system.db.get_rfq_quotations(rfq['rfq_id'])

                    if st.button(f"Simulate quotes from all vendors for RFQ #{rfq['rfq_id']}", key=f"sim_all_{rfq['rfq_id']}"):
                        simulate_all_vendor_quotes(system, rfq)
                        st.success("✅ Simulated quotations from all vendors and triggered AI decision.")
                        st.experimental_rerun()

                    if quotations:
                        st.subheader("Vendor Quotations Received")

                        selected_quotes = [q for q in quotations if q.get('selected', False)]
                        if selected_quotes:
                            selected = selected_quotes[0]
                            st.success(f"✅ **Selected Vendor:** {selected.get('vendor_name')} — Score: {selected.get('score', 0):.1f} — Price: ${selected.get('unit_price', 0):.2f}")

                        # Display quotations in a nice table
                        quote_data = []
                        for quote in quotations:
                            quote_data.append({
                                'Vendor': quote.get('vendor_name', 'Unknown'),
                                'Unit Price': f"${quote.get('unit_price', 0):.2f}",
                                'Delivery Days': quote.get('delivery_days', 'N/A'),
                                'Rating': f"{quote.get('rating', 0):.1f}⭐",
                                'Score': f"{quote.get('score', 0):.1f}",
                                'Status': 'Selected' if quote.get('selected', False) else 'Active'
                            })

                        st.dataframe(quote_data, use_container_width=True)

                        # Show decision if made
                        selected_quotes = [q for q in quotations if q.get('selected', False)]
                        if selected_quotes:
                            selected = selected_quotes[0]
                            st.success(f"✅ **Decision Made**: Selected {selected.get('vendor_name')} with score {selected.get('score', 0):.1f}")
                        else:
                            st.info("⏳ Waiting for more quotations or deadline...")

                    else:
                        st.info("No quotations received yet for this tender.")

                        # Add demo vendor response simulator
                        with st.expander("🎭 Demo: Simulate Vendor Responses", expanded=False):
                            st.markdown("**Simulate vendor email responses for this tender**")

                            col1, col2 = st.columns(2)

                            with col1:
                                vendor_options = [v['name'] for v in system.db.get_all_vendors()]
                                if vendor_options:
                                    selected_vendor = st.selectbox(
                                        "Select Vendor",
                                        vendor_options,
                                        key=f"vendor_{rfq['rfq_id']}"
                                    )

                                    demo_price = st.number_input(
                                        "Quote Price ($)",
                                        min_value=1.0,
                                        value=100.0,
                                        step=10.0,
                                        key=f"price_{rfq['rfq_id']}"
                                    )

                                    demo_delivery = st.slider(
                                        "Delivery Days",
                                        min_value=1,
                                        max_value=30,
                                        value=7,
                                        key=f"delivery_{rfq['rfq_id']}"
                                    )

                            with col2:
                                st.markdown("**Preview Email Response:**")
                                preview_email = f"""
Subject: Quotation for RFQ#{rfq['rfq_id']} - {rfq['item_name']}

Dear Procurement Team,

Thank you for the opportunity to quote on {rfq['item_name']}.

Our quotation:
- Unit Price: ${demo_price:.2f}
- Delivery Time: {demo_delivery} days
- Quantity: {rfq['quantity']} units

We look forward to your business.

Best regards,
{selected_vendor}
Procurement Manager
                                """
                                st.code(preview_email.strip())

                            if st.button(f"📧 Send Demo Response from {selected_vendor}", key=f"send_{rfq['rfq_id']}"):
                                # Simulate adding quotation to database
                                try:
                                    vendor_id = None
                                    for v in system.db.get_all_vendors():
                                        if v['name'] == selected_vendor:
                                            vendor_id = v['vendor_id']
                                            break

                                    if vendor_id:
                                        # Add quotation
                                        quote_id = system.db.add_quotation(
                                            rfq_id=rfq['rfq_id'],
                                            vendor_id=vendor_id,
                                            unit_price=demo_price,
                                            delivery_days=demo_delivery,
                                            terms=f"Demo quotation from {selected_vendor}"
                                        )

                                        # Calculate score using decision agent
                                        quotations = system.db.get_rfq_quotations(rfq['rfq_id'])
                                        if len(quotations) >= 3:  # Enough quotes for decision
                                            decision_result = run_async(system.decision_agent.evaluate_quotations(rfq['rfq_id']))
                                            if decision_result.get('status') == 'decision_made':
                                                st.success(f"🤖 **AI Decision**: {decision_result.get('selected_vendor')} selected with score {decision_result.get('score', 0):.1f}!")
                                            else:
                                                st.info("🤖 AI is evaluating quotations...")

                                        st.success(f"✅ Demo response added from {selected_vendor}!")
                                        st.rerun()  # Refresh the page to show new data
                                    else:
                                        st.error("Vendor not found")

                                except Exception as e:
                                    st.error(f"Error adding demo response: {e}")

                    # Show RFQ details
                    with st.expander("RFQ Details"):
                        st.json({
                            'RFQ ID': rfq['rfq_id'],
                            'Item': rfq['item_name'],
                            'Quantity': rfq['quantity'],
                            'Specifications': rfq.get('specifications', 'N/A'),
                            'Created': rfq.get('created_at', 'N/A'),
                            'Deadline': rfq.get('deadline', 'N/A'),
                            'Status': rfq.get('status', 'Active')
                        })
        else:
            st.info("No active tenders currently. Create a procurement request to start a tender process.")

    except Exception as e:
        st.error(f"Error loading RFQ data: {e}")

    st.subheader("Recent System Log")
    log_lines = tail_log(LOG_FILE, lines=30)
    if log_lines:
        st.code("\n".join(log_lines[-30:]))
    else:
        st.info("No log file found yet. Run the system to generate logs.")

    # Add Vendor Selection Explanation Section
    st.header("How Vendor Selection Works")
    st.markdown("""
    The system automatically evaluates multiple vendor quotations using a weighted scoring algorithm
    to select the best vendor for each procurement request.
    """)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Scoring Criteria & Weights")

        # Create a dataframe for scoring criteria
        import pandas as pd
        scoring_data = {
            'Criterion': ['Price Competitiveness', 'Delivery Time', 'Vendor Rating', 'Quality Score'],
            'Weight': ['30%', '25%', '25%', '20%'],
            'Description': [
                'Lower prices score higher (compared to average)',
                'Faster delivery gets better scores (ideal: 7 days)',
                'Historical vendor performance rating (1-5 stars)',
                'Past quality ratings and reliability'
            ]
        }
        scoring_df = pd.DataFrame(scoring_data)
        st.table(scoring_df)

    with col2:
        st.subheader("Decision Process")
        st.markdown("""
        **1. Collect Quotations**
        - System receives quotes from multiple vendors

        **2. Score Each Quote**
        - Calculate composite score (0-100) using weighted criteria

        **3. Rank Vendors**
        - Sort by total score (highest first)

        **4. Apply Thresholds**
        - Minimum score of 40 required
        - Vendor rating ≥ 3.0 stars

        **5. Select Winner**
        - Choose highest-scoring vendor
        - Automatically place purchase order
        """)

    st.subheader("Example Scoring Calculation")
    st.markdown("For a vendor quotation:")

    # Example calculation
    example_price = 95.0
    example_delivery = 10
    example_rating = 4.2
    example_quality = 4.5

    # Calculate individual scores (simplified)
    price_score = max(0, min(100, 100 * (2.0 - (example_price/100)) / 1.5))  # Assuming reference price = 100
    delivery_score = max(0, min(100, 100 * (30 - example_delivery) / (30 - 7)))
    rating_score = (example_rating / 5.0) * 100
    quality_score = (example_quality / 5.0) * 100

    total_score = (price_score * 0.30 + delivery_score * 0.25 +
                  rating_score * 0.25 + quality_score * 0.20)

    example_data = {
        'Factor': ['Price ($95)', 'Delivery (10 days)', 'Rating (4.2/5)', 'Quality (4.5/5)'],
        'Individual Score': [f"{price_score:.1f}", f"{delivery_score:.1f}", f"{rating_score:.1f}", f"{quality_score:.1f}"],
        'Weighted Score': [f"{price_score*0.30:.1f}", f"{delivery_score*0.25:.1f}", f"{rating_score*0.25:.1f}", f"{quality_score*0.20:.1f}"]
    }
    example_df = pd.DataFrame(example_data)
    st.table(example_df)

    st.markdown(f"**Total Composite Score: {total_score:.1f}/100**")

    st.info("💡 **Key Insight**: The algorithm balances cost, speed, reliability, and quality to ensure optimal procurement decisions.")

    st.markdown("---")
    st.write("Dashboard is connected to the live procurement agent system and database.")


if __name__ == "__main__":
    main()
