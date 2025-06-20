import os
import logging
from typing import List, Dict
from dotenv import load_dotenv
from .kafka_client import KafkaClient

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

class TopicManager:
    """Manages Kafka topic creation and configuration for the sentiment analyzer"""
    
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.kafka_client = KafkaClient(demo_mode=demo_mode)
        
        # Define required topics from environment or defaults
        self.required_topics = [
            os.getenv('KAFKA_TOPIC_TICKETS', 'support-tickets'),
            os.getenv('KAFKA_TOPIC_PROCESSED', 'processed-tickets'),
            os.getenv('KAFKA_TOPIC_RESPONSES', 'ai-responses')
        ]
    
    def initialize_topics(self) -> bool:
        """Initialize all required topics for the sentiment analyzer"""
        logger.info("🚀 Initializing Kafka topics for sentiment analyzer...")
        
        if self.demo_mode:
            logger.info("📝 Demo mode: Topic creation simulated")
            return True
        
        # Check if Kafka client is properly initialized
        if self.kafka_client.demo_mode:
            logger.warning("⚠️  Kafka client fell back to demo mode due to connection issues")
            logger.info("💡 Check your Confluent Cloud credentials in .env file")
            return False
        
        if self.kafka_client.admin_client is None:
            logger.error("❌ Kafka admin client not available")
            logger.info("💡 Verify your Confluent Cloud cluster is running")
            logger.info("💡 Check your API key has admin permissions")
            logger.debug(f"Debug: demo_mode={self.kafka_client.demo_mode}, admin_client={self.kafka_client.admin_client}")
            return False
        
        try:
            # List existing topics first
            existing_topics = self.kafka_client.list_topics()
            logger.info(f"📋 Existing topics in cluster: {existing_topics}")
            
            # Create required topics
            success = self.kafka_client.create_topics(self.required_topics)
            
            if success:
                logger.info("✅ All required topics are available")
                
                # Verify topics were created
                updated_topics = self.kafka_client.list_topics()
                created_topics = [topic for topic in self.required_topics if topic in updated_topics]
                
                logger.info(f"📊 Topics ready for sentiment analysis:")
                for topic in created_topics:
                    logger.info(f"   • {topic}")
                
                return len(created_topics) == len(self.required_topics)
            else:
                logger.error("❌ Failed to create some required topics")
                logger.info("💡 Try creating topics manually in Confluent Cloud UI")
                logger.info("💡 Or check if your API key has topic creation permissions")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize topics: {e}")
            logger.info("💡 Check your Confluent Cloud cluster status")
            logger.info("💡 Verify network connectivity to Confluent Cloud")
            return False
    
    def get_topic_info(self) -> Dict:
        """Get information about all required topics"""
        if self.demo_mode:
            return {
                "demo_mode": True,
                "topics": {topic: "simulated" for topic in self.required_topics}
            }
        
        try:
            existing_topics = self.kafka_client.list_topics()
            topic_info = {
                "cluster_connected": True,
                "topics": {}
            }
            
            for topic in self.required_topics:
                topic_info["topics"][topic] = {
                    "exists": topic in existing_topics,
                    "purpose": self._get_topic_purpose(topic)
                }
            
            return topic_info
            
        except Exception as e:
            logger.error(f"Failed to get topic info: {e}")
            return {
                "cluster_connected": False,
                "error": str(e),
                "topics": {}
            }
    
    def _get_topic_purpose(self, topic: str) -> str:
        """Get human-readable purpose of each topic"""
        purposes = {
            'support-tickets': 'Raw customer support messages',
            'processed-tickets': 'Messages with sentiment analysis results',
            'ai-responses': 'AI-generated responses and escalation decisions'
        }
        
        for key, purpose in purposes.items():
            if key in topic:
                return purpose
        
        return 'Custom topic for sentiment analysis'
    
    def validate_topic_configuration(self) -> bool:
        """Validate that topics are properly configured for production"""
        if self.demo_mode:
            logger.info("Demo mode: Topic validation skipped")
            return True
        
        try:
            # Check if all required topics exist
            existing_topics = self.kafka_client.list_topics()
            missing_topics = [topic for topic in self.required_topics if topic not in existing_topics]
            
            if missing_topics:
                logger.warning(f"⚠️  Missing topics: {missing_topics}")
                return False
            
            logger.info("✅ All required topics exist and are accessible")
            return True
            
        except Exception as e:
            logger.error(f"Topic validation failed: {e}")
            return False
    
    def cleanup_topics(self) -> bool:
        """Clean up topics (use with caution in production)"""
        if self.demo_mode:
            logger.info("Demo mode: Topic cleanup simulated")
            return True
        
        logger.warning("⚠️  Topic cleanup requested - this will delete data!")
        # Implement topic deletion if needed for development
        # NOT recommended for production use
        return True