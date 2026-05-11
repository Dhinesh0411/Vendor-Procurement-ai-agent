"""
Groq LLM Integration Helper
Provides utilities for integrating Groq API with procurement agents.
"""

import os
import logging
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Try to import groq - optional dependency
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)

load_dotenv()


class GroqLLMClient:
    """Client for interacting with Groq API."""
    
    def __init__(self):
        """Initialize Groq client with API key from environment."""
        if not GROQ_AVAILABLE:
            logger.warning("Groq library not installed. Install with: pip install groq")
            self.client = None
            return
            
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            logger.warning("GROQ_API_KEY not set in environment variables")
            self.client = None
            return
            
        self.client = Groq(api_key=api_key)
        self.model = os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768')
        logger.info(f"Groq client initialized with model: {self.model}")
    
    def is_available(self) -> bool:
        """Check if Groq client is available."""
        return self.client is not None
    
    async def analyze_email(self, email_content: str) -> Dict:
        """
        Analyze email content for procurement relevance.
        
        Args:
            email_content: Raw email text
            
        Returns:
            Analysis result with classification and extracted data
        """
        if not self.is_available():
            logger.warning("Groq client not available, skipping email analysis")
            return {'status': 'skipped', 'reason': 'Groq not configured'}
        
        try:
            prompt = f"""Analyze this email for procurement content. Extract:
1. Email type (quotation, RFQ request, delivery update, complaint, other)
2. Vendor name (if any)
3. Key numbers (prices, quantities, delivery times)
4. Action items

Email content:
{email_content}

Respond in JSON format."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                'status': 'success',
                'analysis': message.content[0].text
            }
        except Exception as e:
            logger.error(f"Error analyzing email with Groq: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def score_quotation(self, quotation_data: Dict) -> Dict:
        """
        Score a quotation using Groq AI analysis.
        
        Args:
            quotation_data: Dictionary with price, delivery_time, vendor_rating, etc.
            
        Returns:
            Scoring analysis from Groq
        """
        if not self.is_available():
            logger.warning("Groq client not available, skipping quotation scoring")
            return {'status': 'skipped', 'reason': 'Groq not configured'}
        
        try:
            prompt = f"""Score this vendor quotation on a scale of 1-100, considering:
- Price competitiveness
- Delivery time
- Vendor reliability (rating: {quotation_data.get('vendor_rating', 'N/A')})
- Quality history
- Payment terms

Quotation details:
{quotation_data}

Provide a score and brief justification."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                'status': 'success',
                'scoring': message.content[0].text
            }
        except Exception as e:
            logger.error(f"Error scoring quotation with Groq: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def generate_email_response(self, email_type: str, recipient: str, 
                                     subject: str) -> Dict:
        """
        Generate email response using Groq.
        
        Args:
            email_type: Type of email (quotation_request, order_confirmation, etc.)
            recipient: Recipient vendor name
            subject: Email subject/context
            
        Returns:
            Generated email content
        """
        if not self.is_available():
            logger.warning("Groq client not available, skipping email generation")
            return {'status': 'skipped', 'reason': 'Groq not configured'}
        
        try:
            prompt = f"""Generate a professional procurement email:
Type: {email_type}
Recipient: {recipient}
Subject: {subject}

Keep it concise and professional."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                'status': 'success',
                'email_content': message.content[0].text
            }
        except Exception as e:
            logger.error(f"Error generating email with Groq: {e}")
            return {'status': 'error', 'error': str(e)}


# Singleton instance
_groq_client = None


def get_groq_client() -> GroqLLMClient:
    """Get or create Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqLLMClient()
    return _groq_client
