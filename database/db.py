"""
Database module for procurement management system.
Handles all database operations including vendor management, purchase orders, and inventory.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ProcurementDB:
    """Database manager for procurement operations."""
    
    def __init__(self, db_path: str = "data/vendors.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database with all required tables."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Vendors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                category TEXT,
                rating REAL DEFAULT 0.0,
                on_time_delivery_rate REAL DEFAULT 0.0,
                quality_score REAL DEFAULT 0.0,
                price_competitiveness REAL DEFAULT 0.0,
                total_orders INTEGER DEFAULT 0,
                successful_orders INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Purchase Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL,
                status TEXT DEFAULT 'pending',
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expected_delivery_date TIMESTAMP,
                actual_delivery_date TIMESTAMP,
                quality_rating INTEGER,
                feedback TEXT,
                FOREIGN KEY(vendor_id) REFERENCES vendors(vendor_id)
            )
        """)
        
        # RFQ (Request for Quotation) table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfqs (
                rfq_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                specifications TEXT,
                deadline TIMESTAMP,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                responses_count INTEGER DEFAULT 0
            )
        """)
        
        # Vendor Quotations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                quote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfq_id INTEGER NOT NULL,
                vendor_id INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                delivery_days INTEGER,
                terms TEXT,
                quote_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score REAL DEFAULT 0.0,
                selected BOOLEAN DEFAULT 0,
                FOREIGN KEY(rfq_id) REFERENCES rfqs(rfq_id),
                FOREIGN KEY(vendor_id) REFERENCES vendors(vendor_id)
            )
        """)
        
        # Inventory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL UNIQUE,
                current_stock INTEGER DEFAULT 0,
                min_threshold INTEGER DEFAULT 10,
                max_threshold INTEGER DEFAULT 100,
                reorder_point INTEGER DEFAULT 20,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Communication Log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id INTEGER,
                message_type TEXT,
                subject TEXT,
                content TEXT,
                status TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_received BOOLEAN DEFAULT 0,
                FOREIGN KEY(vendor_id) REFERENCES vendors(vendor_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def add_vendor(self, name: str, email: str, category: str) -> int:
        """Add a new vendor."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)  # 10 second timeout
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vendors (name, email, category)
                VALUES (?, ?, ?)
            """, (name, email, category))
            conn.commit()
            vendor_id = cursor.lastrowid
            conn.close()
            logger.info(f"Vendor added: {name}")
            return vendor_id
        except sqlite3.IntegrityError:
            logger.warning(f"Vendor {name} already exists")
            return self.get_vendor_by_name(name)
    
    def get_vendor_by_name(self, name: str) -> Optional[int]:
        """Get vendor ID by name."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("SELECT vendor_id FROM vendors WHERE name = ?", (name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_all_vendors(self) -> List[Dict]:
        """Get all active vendors."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM vendors WHERE status = 'active'
            ORDER BY rating DESC
        """)
        vendors = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return vendors
    
    def create_rfq(self, item_name: str, quantity: int, 
                   specifications: str, deadline: datetime) -> int:
        """Create a new RFQ."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rfqs (item_name, quantity, specifications, deadline)
            VALUES (?, ?, ?, ?)
        """, (item_name, quantity, specifications, deadline))
        conn.commit()
        rfq_id = cursor.lastrowid
        conn.close()
        logger.info(f"RFQ created: {rfq_id} for {item_name}")
        return rfq_id
    
    def add_quotation(self, rfq_id: int, vendor_id: int, 
                      unit_price: float, delivery_days: int, 
                      terms: str) -> int:
        """Add a vendor quotation for an RFQ."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quotations (rfq_id, vendor_id, unit_price, delivery_days, terms)
            VALUES (?, ?, ?, ?, ?)
        """, (rfq_id, vendor_id, unit_price, delivery_days, terms))
        
        # Update RFQ responses count
        cursor.execute("""
            UPDATE rfqs SET responses_count = responses_count + 1
            WHERE rfq_id = ?
        """, (rfq_id,))
        
        conn.commit()
        quote_id = cursor.lastrowid
        conn.close()
        return quote_id
    
    def get_rfq_quotations(self, rfq_id: int) -> List[Dict]:
        """Get all quotations for an RFQ."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT q.*, v.name as vendor_name, v.rating
            FROM quotations q
            JOIN vendors v ON q.vendor_id = v.vendor_id
            WHERE q.rfq_id = ?
            ORDER BY q.score DESC
        """, (rfq_id,))
        quotations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return quotations
    
    def create_purchase_order(self, vendor_id: int, item_name: str,
                             quantity: int, unit_price: float,
                             expected_delivery: datetime) -> int:
        """Create a purchase order."""
        total_price = quantity * unit_price
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO purchase_orders 
            (vendor_id, item_name, quantity, unit_price, total_price, expected_delivery_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (vendor_id, item_name, quantity, unit_price, total_price, expected_delivery))
        
        # Update vendor stats
        cursor.execute("""
            UPDATE vendors SET total_orders = total_orders + 1
            WHERE vendor_id = ?
        """, (vendor_id,))
        
        conn.commit()
        order_id = cursor.lastrowid
        conn.close()
        logger.info(f"Purchase order created: {order_id}")
        return order_id
    
    def update_order_status(self, order_id: int, status: str, 
                           quality_rating: Optional[int] = None,
                           feedback: Optional[str] = None):
        """Update purchase order status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status == "delivered":
            actual_delivery = datetime.now().isoformat()
            cursor.execute("""
                UPDATE purchase_orders 
                SET status = ?, actual_delivery_date = ?, quality_rating = ?, feedback = ?
                WHERE order_id = ?
            """, (status, actual_delivery, quality_rating, feedback, order_id))
            
            # Update vendor successful orders
            cursor.execute("""
                UPDATE vendors 
                SET successful_orders = successful_orders + 1
                WHERE vendor_id = (
                    SELECT vendor_id FROM purchase_orders WHERE order_id = ?
                )
            """, (order_id,))
        else:
            cursor.execute("""
                UPDATE purchase_orders SET status = ? WHERE order_id = ?
            """, (status, order_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Order {order_id} status updated to {status}")
    
    def get_orders_by_vendor(self, vendor_id: int) -> List[Dict]:
        """Get all orders from a vendor."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM purchase_orders WHERE vendor_id = ?
            ORDER BY order_date DESC
        """, (vendor_id,))
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders
    
    def log_communication(self, vendor_id: Optional[int], message_type: str,
                         subject: str, content: str, status: str = "sent"):
        """Log communication with vendors."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO communication_log 
            (vendor_id, message_type, subject, content, status)
            VALUES (?, ?, ?, ?, ?)
        """, (vendor_id, message_type, subject, content, status))
        conn.commit()
        conn.close()
    
    def update_inventory(self, item_name: str, quantity_change: int):
        """Update inventory stock."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory (item_name, current_stock)
            VALUES (?, ?)
            ON CONFLICT(item_name) DO UPDATE SET
            current_stock = current_stock + ?,
            last_updated = CURRENT_TIMESTAMP
        """, (item_name, quantity_change, quantity_change))
        conn.commit()
        conn.close()
    
    def get_low_stock_items(self) -> List[Dict]:
        """Get items below reorder point."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM inventory 
            WHERE current_stock <= reorder_point
            ORDER BY current_stock ASC
        """)
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return items
    
    def update_vendor_metrics(self, vendor_id: int, on_time: bool, 
                             quality_score: float):
        """Update vendor performance metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_orders = 0
        cursor.execute("""
            SELECT successful_orders, total_orders FROM vendors 
            WHERE vendor_id = ?
        """, (vendor_id,))
        result = cursor.fetchone()
        if result:
            successful, total = result
            on_time_rate = (successful / total * 100) if total > 0 else 0
        
        cursor.execute("""
            UPDATE vendors 
            SET on_time_delivery_rate = ?, quality_score = ?, updated_at = CURRENT_TIMESTAMP
            WHERE vendor_id = ?
        """, (on_time_rate if on_time else 0, quality_score, vendor_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Vendor metrics updated: {vendor_id}")
