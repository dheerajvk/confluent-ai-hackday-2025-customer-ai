import os
import json
import logging
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
from .kafka_client import KafkaClient

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

class DataFlowManager:
    """Manages the complete data flow through Kafka topics for all ticket types"""
    
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.kafka_client = KafkaClient(demo_mode=demo_mode)
        
        # Define topic names from environment
        self.topics = {
            'raw_tickets': os.getenv('KAFKA_TOPIC_TICKETS', 'support-tickets'),
            'processed_tickets': os.getenv('KAFKA_TOPIC_PROCESSED', 'processed-tickets'),
            'ai_responses': os.getenv('KAFKA_TOPIC_RESPONSES', 'ai-responses')
        }
        
        logger.info(f"🔄 DataFlowManager initialized - Demo mode: {demo_mode}")
        logger.info(f"   📋 Topics: {self.topics}")
    
    def send_raw_ticket(self, ticket_data: Dict) -> bool:
        """Send raw ticket to support-tickets topic"""
        try:
            # Add metadata
            enriched_ticket = {
                **ticket_data,
                'source': ticket_data.get('source', 'unknown'),
                'ingestion_timestamp': datetime.now().isoformat(),
                'flow_stage': 'raw_ticket'
            }
            
            if not self.demo_mode:
                self.kafka_client.send_message(
                    topic=self.topics['raw_tickets'],
                    message=enriched_ticket,
                    key=ticket_data.get('ticket_id', 'unknown'),
                    method='ticket.raw_received'
                )
                logger.info(f"📤 Raw ticket sent to Kafka: {ticket_data.get('ticket_id')}")
            else:
                logger.info(f"🎭 Demo mode: Would send raw ticket to {self.topics['raw_tickets']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send raw ticket: {e}")
            return False
    
    def send_processed_ticket(self, processed_data: Dict) -> bool:
        """Send processed ticket with sentiment analysis to processed-tickets topic"""
        try:
            # Add processing metadata
            enriched_data = {
                **processed_data,
                'processing_timestamp': datetime.now().isoformat(),
                'flow_stage': 'processed_ticket'
            }
            
            if not self.demo_mode:
                self.kafka_client.send_message(
                    topic=self.topics['processed_tickets'],
                    message=enriched_data,
                    key=processed_data.get('ticket_id', 'unknown'),
                    method='ticket.processed'
                )
                logger.info(f"📤 Processed ticket sent to Kafka: {processed_data.get('ticket_id')}")
            else:
                logger.info(f"🎭 Demo mode: Would send processed ticket to {self.topics['processed_tickets']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send processed ticket: {e}")
            return False
    
    def send_ai_response(self, response_data: Dict) -> bool:
        """Send AI response to ai-responses topic"""
        try:
            # Add AI metadata
            enriched_response = {
                **response_data,
                'ai_timestamp': datetime.now().isoformat(),
                'flow_stage': 'ai_response'
            }
            
            if not self.demo_mode:
                self.kafka_client.send_message(
                    topic=self.topics['ai_responses'],
                    message=enriched_response,
                    key=response_data.get('ticket_id', 'unknown'),
                    method='ai.response_generated'
                )
                logger.info(f"📤 AI response sent to Kafka: {response_data.get('ticket_id')}")
            else:
                logger.info(f"🎭 Demo mode: Would send AI response to {self.topics['ai_responses']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send AI response: {e}")
            return False
    
    def process_complete_ticket_flow(self, raw_ticket: Dict, processed_ticket: Dict, ai_response: Dict) -> bool:
        """Process complete ticket flow through all three topics"""
        try:
            ticket_id = raw_ticket.get('ticket_id', 'unknown')
            source = raw_ticket.get('source', 'unknown')
            
            logger.info(f"🔄 Processing complete flow for ticket {ticket_id} from {source}")
            
            # Step 1: Send raw ticket
            if not self.send_raw_ticket(raw_ticket):
                logger.error(f"❌ Failed at step 1 (raw ticket) for {ticket_id}")
                return False
            
            # Step 2: Send processed ticket
            if not self.send_processed_ticket(processed_ticket):
                logger.error(f"❌ Failed at step 2 (processed ticket) for {ticket_id}")
                return False
            
            # Step 3: Send AI response
            ai_response_with_ticket_id = {
                **ai_response,
                'ticket_id': ticket_id,
                'original_message': raw_ticket.get('message', ''),
                'sentiment_analysis': {
                    'sentiment': processed_ticket.get('sentiment'),
                    'polarity': processed_ticket.get('polarity'),
                    'priority': processed_ticket.get('priority'),
                    'needs_escalation': processed_ticket.get('needs_escalation')
                }
            }
            
            if not self.send_ai_response(ai_response_with_ticket_id):
                logger.error(f"❌ Failed at step 3 (AI response) for {ticket_id}")
                return False
            
            logger.info(f"✅ Complete flow processed successfully for ticket {ticket_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Complete flow processing failed: {e}")
            return False
    
    def get_flow_status(self) -> Dict:
        """Get status of data flow"""
        if self.demo_mode:
            return {
                'mode': 'demo',
                'kafka_connected': False,
                'topics_available': self.topics,
                'flow_active': True
            }
        
        try:
            # Check if topics exist
            existing_topics = self.kafka_client.list_topics()
            topics_status = {}
            
            for topic_name, topic_key in self.topics.items():
                topics_status[topic_name] = {
                    'name': topic_key,
                    'exists': topic_key in existing_topics,
                    'ready': topic_key in existing_topics
                }
            
            return {
                'mode': 'production',
                'kafka_connected': not self.kafka_client.demo_mode,
                'topics_status': topics_status,
                'flow_active': all(status['ready'] for status in topics_status.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to get flow status: {e}")
            return {
                'mode': 'production',
                'kafka_connected': False,
                'error': str(e),
                'flow_active': False
            }
    
    def consume_from_topic(self, topic_name: str, callback_function) -> bool:
        """Start consuming from a specific topic"""
        if self.demo_mode:
            logger.info(f"🎭 Demo mode: Would consume from {topic_name}")
            return True
        
        try:
            topic_key = self.topics.get(topic_name)
            if not topic_key:
                logger.error(f"Unknown topic name: {topic_name}")
                return False
            
            logger.info(f"📥 Starting consumer for topic: {topic_key}")
            self.kafka_client.consume_messages([topic_key], callback_function)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start consumer for {topic_name}: {e}")
            return False