#!/usr/bin/env python3
"""
Main entry point for Confluent AI Support Optimizer
Real-Time Customer Sentiment & Support Optimizer
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def setup_logging():
    """Setup logging configuration"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('kafka').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def check_environment():
    """Check required environment variables"""
    required_vars = ['ANTHROPIC_API_KEY']
    optional_vars = ['CONFLUENT_BOOTSTRAP_SERVERS', 'CONFLUENT_API_KEY', 'CONFLUENT_API_SECRET']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        print("Please set these in your .env file")
        return False
    
    if missing_optional:
        print(f"⚠️  Missing optional variables (using demo mode): {', '.join(missing_optional)}")
        print("For full Confluent integration, set these in your .env file")
    
    return True

def print_banner():
    """Print application banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  🚀 CONFLUENT AI SUPPORT OPTIMIZER                                           ║
║                                                                               ║
║  Real-Time Customer Sentiment & Support Optimizer                            ║
║  Powered by: Confluent Cloud + Claude AI + Gradio                           ║
║                                                                               ║
║  🏆 Hackathon Demo - Built for Confluent AI Day India                       ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📋 Features:
   • Real-time sentiment analysis with Claude AI
   • AI-powered response generation with context
   • Live streaming dashboard with Kafka
   • Automatic escalation detection
   • Customer context management (MCP-like)
   • Interactive Gradio interface

🔧 Tech Stack:
   • Confluent Kafka for streaming
   • Claude AI for sentiment & response generation
   • Gradio for interactive UI
   • Python asyncio for real-time processing


"""
    print(banner)

def main():
    """Main application entry point"""
    try:
        # Print banner
        print_banner()
        
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # Check environment
        if not check_environment():
            sys.exit(1)
        
        logger.info("🚀 Starting Confluent AI Support Optimizer...")
        
        # Get demo mode and port from environment
        demo_mode = os.getenv('DEMO_MODE', 'true').lower() == 'true'
        port = int(os.getenv('GRADIO_PORT', 7860))
        
        logger.info(f"🎯 Demo mode: {demo_mode}")
        
        # Initialize Kafka topics if not in demo mode
        if not demo_mode:
            logger.info("🔧 Initializing Kafka topics for production mode...")
            from streaming.topic_manager import TopicManager
            
            topic_manager = TopicManager(demo_mode=demo_mode)
            
            # Create required topics
            topics_initialized = topic_manager.initialize_topics()
            
            if topics_initialized:
                logger.info("✅ Kafka topics initialized successfully")
                
                # Get and log topic information
                topic_info = topic_manager.get_topic_info()
                if topic_info.get("cluster_connected"):
                    logger.info("📊 Topic configuration:")
                    for topic, info in topic_info["topics"].items():
                        status = "✅" if info["exists"] else "❌"
                        logger.info(f"   {status} {topic}: {info['purpose']}")
                else:
                    logger.warning("⚠️  Could not verify topic configuration")
            else:
                logger.error("❌ Failed to initialize Kafka topics")
                logger.info("💡 You can create topics manually in Confluent Cloud UI")
                logger.info("💡 Or run: python3 test_confluent.py to diagnose issues")
                logger.info("💡 The application will continue but may have limited functionality")
        
        logger.info(f"🌐 Starting dashboard on port {port}")
        
        # Import and run the main application
        from ui.dashboard import launch_dashboard
        
        # Run the Gradio dashboard
        launch_dashboard(demo_mode=demo_mode, port=port)
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        sys.exit(0)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed: uv sync")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.exception("Unexpected error occurred")
        sys.exit(1)

if __name__ == "__main__":
    main()