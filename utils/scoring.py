"""
Scoring module for vendor evaluation and quotation ranking.
Uses multiple criteria to calculate comprehensive vendor scores.
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class VendorScorer:
    """Calculate vendor scores based on multiple metrics."""
    
    # Weights for scoring criteria
    WEIGHTS = {
        'price': 0.30,
        'delivery_time': 0.25,
        'vendor_rating': 0.25,
        'quality': 0.20
    }
    
    # Thresholds
    MIN_ACCEPTABLE_RATING = 3.0
    MAX_DELIVERY_DAYS = 30
    IDEAL_DELIVERY_DAYS = 7
    
    @classmethod
    def score_quotation(cls, quotation: Dict, vendor: Dict, 
                       rfq_quantity: int, reference_price: float) -> float:
        """
        Calculate composite score for a quotation.
        
        Args:
            quotation: Quotation data
            vendor: Vendor data
            rfq_quantity: Quantity in RFQ
            reference_price: Reference price for comparison
            
        Returns:
            Composite score (0-100)
        """
        scores = {}
        
        # Price score (0-100): Lower is better
        price_score = cls._score_price(
            quotation['unit_price'],
            reference_price,
            rfq_quantity
        )
        scores['price'] = price_score
        
        # Delivery time score (0-100): Closer to ideal is better
        delivery_score = cls._score_delivery_time(quotation['delivery_days'])
        scores['delivery_time'] = delivery_score
        
        # Vendor rating score (0-100): Based on historical performance
        rating_score = cls._score_vendor_rating(vendor)
        scores['vendor_rating'] = rating_score
        
        # Quality score (0-100): Based on past quality ratings
        quality_score = cls._score_quality(vendor)
        scores['quality'] = quality_score
        
        # Calculate weighted composite score
        composite_score = sum(
            scores[criterion] * cls.WEIGHTS[criterion]
            for criterion in cls.WEIGHTS
        )
        
        logger.debug(f"Quotation scores: {scores}, Composite: {composite_score:.2f}")
        return round(composite_score, 2)
    
    @classmethod
    def _score_price(cls, unit_price: float, reference_price: float,
                    quantity: int) -> float:
        """Score based on price competitiveness."""
        if reference_price == 0:
            return 50.0
        
        price_ratio = unit_price / reference_price
        
        # +100 for best price (50% less), -100 for worst (double)
        if price_ratio <= 0.5:
            return 100.0
        elif price_ratio >= 2.0:
            return 0.0
        else:
            # Linear scale
            return 100 * (2.0 - price_ratio) / 1.5
    
    @classmethod
    def _score_delivery_time(cls, delivery_days: int) -> float:
        """Score based on delivery time."""
        if delivery_days <= cls.IDEAL_DELIVERY_DAYS:
            return 100.0
        elif delivery_days >= cls.MAX_DELIVERY_DAYS:
            return 0.0
        else:
            # Linear decrease
            return 100 * (cls.MAX_DELIVERY_DAYS - delivery_days) / (cls.MAX_DELIVERY_DAYS - cls.IDEAL_DELIVERY_DAYS)
    
    @classmethod
    def _score_vendor_rating(cls, vendor: Dict) -> float:
        """Score based on vendor overall rating."""
        rating = vendor.get('rating', 0.0)
        
        # Convert 0-5 rating to 0-100
        if rating >= 4.5:
            return 100.0
        elif rating < cls.MIN_ACCEPTABLE_RATING:
            return 0.0  # Fail if rating too low
        else:
            return (rating / 5.0) * 100
    
    @classmethod
    def _score_quality(cls, vendor: Dict) -> float:
        """Score based on quality history."""
        quality_score = vendor.get('quality_score', 0.0)
        
        if quality_score >= 4.5:
            return 100.0
        elif quality_score < 3.0:
            return 20.0
        else:
            return (quality_score / 5.0) * 100
    
    @classmethod
    def rank_quotations(cls, quotations: List[Dict], vendors: Dict,
                       rfq_quantity: int) -> List[Dict]:
        """
        Rank quotations and return sorted by score.
        
        Args:
            quotations: List of quotation records
            vendors: Dict mapping vendor_id to vendor data
            rfq_quantity: Quantity in RFQ
            
        Returns:
            Sorted list of quotations with scores
        """
        # Calculate reference price (average or median)
        prices = [q['unit_price'] for q in quotations]
        reference_price = sum(prices) / len(prices) if prices else 0
        
        scored_quotations = []
        for quotation in quotations:
            vendor = vendors.get(quotation['vendor_id'], {})
            
            # Filter out vendors with poor ratings
            if vendor.get('rating', 0) < cls.MIN_ACCEPTABLE_RATING:
                score = 0
            else:
                score = cls.score_quotation(
                    quotation, vendor, rfq_quantity, reference_price
                )
            
            scored_quotations.append({
                **quotation,
                'score': score,
                'vendor_name': vendor.get('name', 'Unknown')
            })
        
        # Sort by score descending
        scored_quotations.sort(key=lambda x: x['score'], reverse=True)
        return scored_quotations


class ProcurementAnalyzer:
    """Analyze procurement data and provide recommendations."""
    
    @staticmethod
    def analyze_vendor_performance(orders: List[Dict]) -> Dict:
        """Analyze vendor performance metrics."""
        if not orders:
            return {}
        
        total_orders = len(orders)
        delivered = sum(1 for o in orders if o['status'] == 'delivered')
        on_time = sum(1 for o in orders if o.get('actual_delivery_date') and 
                     o.get('expected_delivery_date'))
        
        # Calculate average quality rating
        quality_ratings = [o['quality_rating'] for o in orders 
                          if o.get('quality_rating')]
        avg_quality = (sum(quality_ratings) / len(quality_ratings) 
                      if quality_ratings else 0)
        
        return {
            'total_orders': total_orders,
            'delivery_rate': (delivered / total_orders * 100) if total_orders else 0,
            'on_time_rate': (on_time / delivered * 100) if delivered else 0,
            'average_quality': avg_quality,
            'pending_orders': sum(1 for o in orders if o['status'] == 'pending'),
            'failed_orders': sum(1 for o in orders if o['status'] == 'cancelled')
        }
    
    @staticmethod
    def suggest_vendors(vendors: List[Dict], required_quantity: int,
                       budget: float) -> List[Dict]:
        """
        Suggest best vendors based on criteria.
        
        Returns top 3 vendors with best overall scores.
        """
        ranked = sorted(vendors, key=lambda v: v.get('rating', 0), reverse=True)
        
        suggestions = []
        for vendor in ranked[:5]:  # Check top 5 vendors
            total_cost = required_quantity * vendor.get('price_competitiveness', 1.0)
            if total_cost <= budget:
                suggestions.append({
                    'vendor_id': vendor['vendor_id'],
                    'name': vendor['name'],
                    'rating': vendor.get('rating', 0),
                    'estimated_cost': total_cost,
                    'delivery_days': vendor.get('on_time_delivery_rate', 0),
                    'quality_score': vendor.get('quality_score', 0)
                })
        
        return suggestions[:3]
    
    @staticmethod
    def identify_risk_vendors(vendors: List[Dict]) -> List[Dict]:
        """Identify vendors with performance issues."""
        risk_vendors = [
            v for v in vendors
            if v.get('rating', 5) < 3.5 or 
               v.get('on_time_delivery_rate', 100) < 70
        ]
        return sorted(risk_vendors, 
                     key=lambda v: v.get('rating', 0))
