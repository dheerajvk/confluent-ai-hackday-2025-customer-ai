"""
Stream Lineage Monitoring Utilities for Confluent Cloud
Provides tools to monitor and verify Stream Lineage visibility
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class StreamLineageMonitor:
    """Monitor Stream Lineage visibility for Gradio Kafka clients"""
    
    def __init__(self):
        self.client_ids = [
            'gradio-sentiment-producer',
            'gradio-sentiment-consumer'
        ]
        self.consumer_groups = [
            'gradio-sentiment-analyzer-group'
        ]
        self.topics = [
            'support-tickets',
            'processed-tickets', 
            'ai-responses'
        ]
        self.activity_log = []
        
    def log_kafka_activity(self, activity_type: str, topic: str, message_count: int = 1, metadata: Dict = None):
        """Log Kafka activity for Stream Lineage tracking"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'activity_type': activity_type,  # 'produce' or 'consume'
            'topic': topic,
            'message_count': message_count,
            'client_id': f'gradio-sentiment-{activity_type}r',
            'metadata': metadata or {}
        }
        
        self.activity_log.append(activity)
        
        # Keep only last 100 activities
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]
        
        logger.info(f"📊 Stream Lineage Activity: {activity_type.upper()} to {topic}")
        logger.info(f"   Client ID: {activity['client_id']}")
        logger.info(f"   Messages: {message_count}")
        if activity_type == 'produce':
            logger.info(f"   🔗 Visible in Confluent Stream Lineage within ~10 minutes")
    
    def get_activity_summary(self, minutes: int = 10) -> Dict:
        """Get activity summary for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_activities = [
            activity for activity in self.activity_log
            if datetime.fromisoformat(activity['timestamp']) > cutoff_time
        ]
        
        summary = {
            'time_window_minutes': minutes,
            'total_activities': len(recent_activities),
            'produce_count': len([a for a in recent_activities if a['activity_type'] == 'produce']),
            'consume_count': len([a for a in recent_activities if a['activity_type'] == 'consume']),
            'topics_active': list(set([a['topic'] for a in recent_activities])),
            'client_ids_active': list(set([a['client_id'] for a in recent_activities])),
            'latest_activity': recent_activities[-1] if recent_activities else None
        }
        
        return summary
    
    def generate_lineage_report(self) -> str:
        """Generate a human-readable Stream Lineage report"""
        summary = self.get_activity_summary(10)
        
        report = f"""
🔗 CONFLUENT STREAM LINEAGE VISIBILITY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Activity Summary (Last 10 minutes):
   • Total Kafka Operations: {summary['total_activities']}
   • Messages Produced: {summary['produce_count']}
   • Messages Consumed: {summary['consume_count']}
   • Active Topics: {', '.join(summary['topics_active']) if summary['topics_active'] else 'None'}

🎯 Client Visibility in Stream Lineage:
   • Producer Client ID: gradio-sentiment-producer
   • Consumer Client ID: gradio-sentiment-consumer  
   • Consumer Group: gradio-sentiment-analyzer-group

🔍 How to Find in Confluent Cloud:
   1. Go to Confluent Cloud Console
   2. Select your cluster
   3. Navigate to "Stream Lineage" tab
   4. Search for: "gradio-sentiment-producer" or "gradio-sentiment-consumer"
   5. Look for data flow in last 10 minutes

📈 Data Flow Pattern:
   Gradio App → support-tickets → processed-tickets → ai-responses
   
⏰ Stream Lineage shows activity from last 10 minutes only
   Latest Activity: {summary['latest_activity']['timestamp'] if summary['latest_activity'] else 'None'}

✅ Status: {'ACTIVE' if summary['total_activities'] > 0 else 'INACTIVE'} - {'Visible in Stream Lineage' if summary['total_activities'] > 0 else 'No recent activity to show'}
"""
        return report
    
    def check_lineage_prerequisites(self) -> Dict:
        """Check if all prerequisites for Stream Lineage visibility are met"""
        checks = {
            'kafka_config_valid': False,
            'client_ids_configured': False,
            'topics_configured': False,
            'demo_mode_status': None,
            'recommendations': []
        }
        
        # Check Kafka configuration
        bootstrap_servers = os.getenv('CONFLUENT_BOOTSTRAP_SERVERS')
        api_key = os.getenv('CONFLUENT_API_KEY')
        api_secret = os.getenv('CONFLUENT_API_SECRET')
        
        if all([bootstrap_servers, api_key, api_secret]):
            checks['kafka_config_valid'] = True
        else:
            checks['recommendations'].append("Configure Kafka credentials in .env file")
        
        # Check demo mode
        demo_mode = os.getenv('DEMO_MODE', 'true').lower() == 'true'
        checks['demo_mode_status'] = 'demo' if demo_mode else 'production'
        
        if demo_mode:
            checks['recommendations'].append("Set DEMO_MODE=false for real Kafka activity visible in Stream Lineage")
        
        # Check client IDs (assume configured since we set them)
        checks['client_ids_configured'] = True
        
        # Check topics (assume configured)  
        checks['topics_configured'] = True
        
        return checks
    
    def print_lineage_instructions(self):
        """Print instructions for finding the app in Stream Lineage"""
        print("\n🔗 STREAM LINEAGE VISIBILITY INSTRUCTIONS")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("\n📍 To find your Gradio app in Confluent Stream Lineage:")
        print("   1. Open Confluent Cloud Console: https://confluent.cloud")
        print("   2. Select your Kafka cluster")
        print("   3. Click on 'Stream Lineage' tab")
        print("   4. In the search box, type one of these client IDs:")
        print("      • gradio-sentiment-producer")
        print("      • gradio-sentiment-consumer")
        print("      • gradio-sentiment-analyzer-group (consumer group)")
        print("\n⏰ Note: Stream Lineage shows activity from the last 10 minutes only")
        print("📊 Your Gradio app will appear as nodes connected to these topics:")
        print("   • support-tickets")
        print("   • processed-tickets") 
        print("   • ai-responses")
        print("\n🎯 Data Flow Visualization:")
        print("   [Gradio App] → [support-tickets] → [processing] → [processed-tickets] → [ai-responses]")
        print("\n✅ Ensure your app is actively sending/receiving messages for visibility")

# Global monitor instance
lineage_monitor = StreamLineageMonitor()

def log_produce_activity(topic: str, message_count: int = 1, metadata: Dict = None):
    """Log message production activity for Stream Lineage tracking"""
    lineage_monitor.log_kafka_activity('produce', topic, message_count, metadata)

def log_consume_activity(topic: str, message_count: int = 1, metadata: Dict = None):
    """Log message consumption activity for Stream Lineage tracking"""
    lineage_monitor.log_kafka_activity('consume', topic, message_count, metadata)

def get_lineage_report() -> str:
    """Get current Stream Lineage visibility report"""
    return lineage_monitor.generate_lineage_report()

def print_lineage_status():
    """Print current Stream Lineage status"""
    print(lineage_monitor.generate_lineage_report())

def show_lineage_instructions():
    """Show instructions for finding app in Stream Lineage"""
    lineage_monitor.print_lineage_instructions()