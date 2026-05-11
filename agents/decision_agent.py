"""
Decision Agent - Make procurement decisions based on quotations.
Evaluates quotations and selects best vendors.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from utils.scoring import VendorScorer, ProcurementAnalyzer

logger = logging.getLogger(__name__)


class DecisionAgent:
    """Make intelligent procurement decisions."""
    
    def __init__(self, db, order_agent=None):
        """
        Initialize decision agent.
        
        Args:
            db: Database instance
            order_agent: Order agent instance for placing orders
        """
        self.db = db
        self.order_agent = order_agent
        self.decision_history = {}
    
    async def evaluate_quotations(self, rfq_id: int) -> Dict:
        """
        Evaluate all quotations for an RFQ.
        
        Args:
            rfq_id: RFQ ID
            
        Returns:
            Decision result with selected vendor
        """
        try:
            logger.info(f"Evaluating quotations for RFQ {rfq_id}")
            
            # Get RFQ details
            # Get quotations
            quotations = self.db.get_rfq_quotations(rfq_id)
            
            if not quotations:
                logger.warning(f"No quotations found for RFQ {rfq_id}")
                return {
                    'status': 'no_quotations',
                    'rfq_id': rfq_id,
                    'decision': None
                }
            
            logger.info(f"Found {len(quotations)} quotations for RFQ {rfq_id}")
            
            # Score quotations
            scored_quotations = await self._score_quotations(quotations)
            
            # Select best quotation
            best_quotation = scored_quotations[0]
            
            logger.info(f"Best quotation selected: {best_quotation}")
            
            # Check if decision is acceptable
            if best_quotation['score'] < 40:  # Minimum acceptable score
                logger.warning(f"Best quotation score {best_quotation['score']} below threshold")
                return {
                    'status': 'no_acceptable_quotation',
                    'rfq_id': rfq_id,
                    'best_score': best_quotation['score']
                }
            
            # Persist selected quotation in the database
            if hasattr(self.db, 'mark_quotation_selected'):
                self.db.mark_quotation_selected(best_quotation['quote_id'])

            # Store decision
            self.decision_history[rfq_id] = {
                'decision_time': datetime.now(),
                'selected_vendor': best_quotation['vendor_id'],
                'selected_quote': best_quotation['quote_id'],
                'score': best_quotation['score'],
                'all_scores': [q['score'] for q in scored_quotations]
            }
            
            # Trigger order placement
            if self.order_agent:
                await self.order_agent.place_purchase_order(
                    rfq_id, best_quotation['vendor_id'], best_quotation
                )
            
            return {
                'status': 'decision_made',
                'rfq_id': rfq_id,
                'selected_vendor_id': best_quotation['vendor_id'],
                'selected_vendor': best_quotation['vendor_name'],
                'unit_price': best_quotation['unit_price'],
                'delivery_days': best_quotation['delivery_days'],
                'score': best_quotation['score'],
                'alternatives': scored_quotations[1:4]  # Top 3 alternatives
            }
            
        except Exception as e:
            logger.error(f"Error evaluating quotations: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _score_quotations(self, quotations: List[Dict]) -> List[Dict]:
        """
        Score and rank quotations using vendor scorer.
        
        Args:
            quotations: List of quotation dicts
            
        Returns:
            Sorted list of quotations with scores
        """
        # Build vendor dict
        vendors = {}
        for q in quotations:
            if q['vendor_id'] not in vendors:
                vendors[q['vendor_id']] = {
                    'vendor_id': q['vendor_id'],
                    'name': q.get('vendor_name', 'Unknown'),
                    'rating': q.get('rating', 3.0),
                    'quality_score': 3.5,
                    'on_time_delivery_rate': 85.0,
                    'price_competitiveness': 1.0
                }
        
        # Calculate reference price
        prices = [q['unit_price'] for q in quotations]
        reference_price = sum(prices) / len(prices) if prices else 0
        
        # Score each quotation
        for quotation in quotations:
            vendor = vendors[quotation['vendor_id']]
            score = VendorScorer.score_quotation(
                quotation,
                vendor,
                quotation.get('quantity', 1),
                reference_price
            )
            quotation['score'] = score
        
        # Sort by score
        return sorted(quotations, key=lambda x: x['score'], reverse=True)
    
    async def compare_quotations(self, rfq_id: int) -> Dict:
        """
        Generate detailed comparison of quotations.
        
        Args:
            rfq_id: RFQ ID
            
        Returns:
            Comparison report
        """
        quotations = self.db.get_rfq_quotations(rfq_id)
        
        if not quotations:
            return {'status': 'no_quotations', 'rfq_id': rfq_id}
        
        # Build comparison
        comparison = {
            'rfq_id': rfq_id,
            'total_vendors': len(quotations),
            'quotations': []
        }
        
        # Calculate price range
        prices = [q['unit_price'] for q in quotations]
        
        for i, q in enumerate(sorted(quotations, key=lambda x: x['unit_price'])):
            q_data = {
                'rank': i + 1,
                'vendor': q['vendor_name'],
                'unit_price': q['unit_price'],
                'price_vs_min': f"+{(q['unit_price']/min(prices) - 1)*100:.1f}%" if i > 0 else "Lowest",
                'delivery_days': q['delivery_days'],
                'terms': q.get('terms', ''),
                'vendor_rating': q['rating']
            }
            comparison['quotations'].append(q_data)
        
        return comparison
    
    async def apply_business_rules(self, quotations: List[Dict],
                                  business_rules: Dict) -> List[Dict]:
        """
        Apply business rules to filter/adjust quotations.
        
        Args:
            quotations: List of quotations
            business_rules: Dict with rules like max_price, preferred_vendors, etc.
            
        Returns:
            Filtered/adjusted quotations
        """
        max_price = business_rules.get('max_price')
        preferred_vendors = business_rules.get('preferred_vendors', [])
        min_rating = business_rules.get('min_vendor_rating', 3.0)
        max_delivery_days = business_rules.get('max_delivery_days', 30)
        
        filtered = []
        
        for q in quotations:
            # Price check
            if max_price and q['unit_price'] > max_price:
                continue
            
            # Rating check
            if q.get('rating', 0) < min_rating:
                continue
            
            # Delivery time check
            if q.get('delivery_days', 999) > max_delivery_days:
                continue
            
            # Boost score for preferred vendors
            if q['vendor_id'] in preferred_vendors:
                q['score'] = q.get('score', 50) * 1.1
            
            filtered.append(q)
        
        return sorted(filtered, key=lambda x: x.get('score', 0), reverse=True)
    
    def get_decision_rationale(self, rfq_id: int) -> Dict:
        """Get detailed rationale for a procurement decision."""
        if rfq_id not in self.decision_history:
            return {'status': 'no_decision', 'rfq_id': rfq_id}
        
        decision = self.decision_history[rfq_id]
        
        return {
            'rfq_id': rfq_id,
            'decision_time': decision['decision_time'].isoformat(),
            'selected_vendor_id': decision['selected_vendor'],
            'selection_score': decision['score'],
            'score_distribution': decision['all_scores'],
            'average_score': sum(decision['all_scores']) / len(decision['all_scores']),
            'rationale': f"""
                Selected vendor based on:
                1. Best composite score: {decision['score']:.2f}/100
                2. Price competitiveness
                3. Delivery time
                4. Historical vendor performance
                5. Quality ratings
                
                Alternative vendors available with scores:
                {', '.join([f'{s:.1f}' for s in decision['all_scores'][1:4]])}
            """
        }
    
    async def handle_no_suitable_quotations(self, rfq_id: int) -> Dict:
        """
        Handle case where no suitable quotations received.
        
        Strategies:
        - Re-contact non-responsive vendors
        - Relax specifications
        - Increase budget
        - Use emergency supplier
        """
        logger.warning(f"No suitable quotations for RFQ {rfq_id}")
        
        quotations = self.db.get_rfq_quotations(rfq_id)
        
        return {
            'rfq_id': rfq_id,
            'status': 'escalated',
            'quotations_received': len(quotations),
            'recommended_actions': [
                'Re-send RFQ to additional vendors',
                'Review and relax specifications',
                'Consider increasing budget by 10-20%',
                'Check with emergency suppliers',
                'Escalate to procurement manager'
            ],
            'action_plan': 'Waiting for manual review'
        }
    
    def get_decision_metrics(self) -> Dict:
        """Get metrics on decision-making performance."""
        total_decisions = len(self.decision_history)
        
        if total_decisions == 0:
            return {'total_decisions': 0, 'average_score': 0}
        
        scores = [d['score'] for d in self.decision_history.values()]
        avg_score = sum(scores) / len(scores)
        
        return {
            'total_decisions': total_decisions,
            'average_selection_score': round(avg_score, 2),
            'min_score': min(scores),
            'max_score': max(scores),
            'decisions': list(self.decision_history.keys())
        }
