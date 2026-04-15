import asyncio
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

    st.subheader("Recent System Log")
    log_lines = tail_log(LOG_FILE, lines=30)
    if log_lines:
        st.code("\n".join(log_lines[-30:]))
    else:
        st.info("No log file found yet. Run the system to generate logs.")

    st.markdown("---")
    st.write("Dashboard is connected to the live procurement agent system and database.")


if __name__ == "__main__":
    main()
