from textblob import TextBlob
from typing import Dict, List, Tuple
import re
import json
from datetime import datetime

class SentimentAnalyzer:
    def __init__(self):
        self.escalation_keywords = [
            'angry', 'furious', 'hate', 'terrible', 'awful', 'worst',
            'cancel', 'refund', 'complaint', 'frustrated', 'disappointed',
            'unacceptable', 'disgusted', 'outraged', 'livid'
        ]
        
        self.urgency_keywords = [
            'urgent', 'asap', 'immediately', 'emergency', 'critical',
            'broken', 'not working', 'down', 'stuck', 'help'
        ]
    
    def analyze_sentiment(self, text: str) -> Dict:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Classify sentiment
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Check for escalation triggers
        escalation_score = self._calculate_escalation_score(text.lower())
        urgency_score = self._calculate_urgency_score(text.lower())
        
        # Determine priority
        priority = self._determine_priority(polarity, escalation_score, urgency_score)
        
        return {
            "sentiment": sentiment,
            "polarity": polarity,
            "subjectivity": subjectivity,
            "escalation_score": escalation_score,
            "urgency_score": urgency_score,
            "priority": priority,
            "needs_escalation": escalation_score > 0.5 or polarity < -0.5,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_escalation_score(self, text: str) -> float:
        score = 0
        for keyword in self.escalation_keywords:
            if keyword in text:
                score += 1
        return min(score / len(self.escalation_keywords), 1.0)
    
    def _calculate_urgency_score(self, text: str) -> float:
        score = 0
        for keyword in self.urgency_keywords:
            if keyword in text:
                score += 1
        return min(score / len(self.urgency_keywords), 1.0)
    
    def _determine_priority(self, polarity: float, escalation_score: float, urgency_score: float) -> str:
        if escalation_score > 0.5 or polarity < -0.6:
            return "high"
        elif urgency_score > 0.3 or polarity < -0.3:
            return "medium"
        else:
            return "low"

class TicketProcessor:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.processed_tickets = []
    
    def process_ticket(self, ticket_data: Dict) -> Dict:
        message = ticket_data.get('message', '')
        customer_id = ticket_data.get('customer_id', 'unknown')
        ticket_id = ticket_data.get('ticket_id', 'unknown')
        
        # Analyze sentiment
        sentiment_result = self.sentiment_analyzer.analyze_sentiment(message)
        
        # Create processed ticket
        processed_ticket = {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "original_message": message,
            **sentiment_result,
            "processed_at": datetime.now().isoformat()
        }
        
        self.processed_tickets.append(processed_ticket)
        return processed_ticket
    
    def get_dashboard_data(self) -> Dict:
        if not self.processed_tickets:
            return {
                "total_tickets": 0,
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "priority_distribution": {"high": 0, "medium": 0, "low": 0},
                "escalation_rate": 0.0,
                "recent_tickets": []
            }
        
        total = len(self.processed_tickets)
        
        # Sentiment distribution
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        priority_counts = {"high": 0, "medium": 0, "low": 0}
        escalations = 0
        
        for ticket in self.processed_tickets:
            sentiment_counts[ticket["sentiment"]] += 1
            priority_counts[ticket["priority"]] += 1
            if ticket["needs_escalation"]:
                escalations += 1
        
        return {
            "total_tickets": total,
            "sentiment_distribution": sentiment_counts,
            "priority_distribution": priority_counts,
            "escalation_rate": escalations / total if total > 0 else 0.0,
            "recent_tickets": self.processed_tickets[-10:]
        }