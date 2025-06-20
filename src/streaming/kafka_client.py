import os
import json
import asyncio
from typing import Dict, Callable, Optional
from confluent_kafka import Producer, Consumer, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.serialization import SerializationContext, MessageField, StringSerializer, StringDeserializer
import logging
from datetime import datetime
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Setup logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import JSON-RPC 2.0 for standardized messaging
try:
    from ..core.jsonrpc import JsonRpcProcessor, JsonRpcRequest, JsonRpcResponse
except ImportError:
    # Fallback if import fails
    JsonRpcProcessor = None
    JsonRpcRequest = None
    JsonRpcResponse = None

# Import Schema Registry client
get_schema_registry = None
schema_registry_import_error = None

try:
    from ..schemas.schema_registry_client import get_schema_registry
    logger.debug("✅ Schema Registry client imported successfully")
except ImportError as e:
    schema_registry_import_error = str(e)
    logger.debug(f"Schema Registry import failed: {e}")
    get_schema_registry = None

class KafkaClient:
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.producer = None
        self.consumer = None
        self.admin_client = None
        self.jsonrpc_processor = JsonRpcProcessor() if JsonRpcProcessor else None
        self.use_jsonrpc = os.getenv('USE_JSONRPC_2_0', 'true').lower() == 'true'
        
        # Initialize Schema Registry
        self.schema_registry = None
        self.use_schema_registry = True
        
        if demo_mode:
            logger.info("📝 Demo mode: Schema Registry disabled")
            self.use_schema_registry = False
        elif not get_schema_registry:
            if 'confluent_kafka' in schema_registry_import_error:
                logger.warning("⚠️  confluent-kafka package not installed - Schema Registry unavailable")
                logger.info("💡 To enable Avro serialization, install: pip install 'confluent-kafka[avro,schemaregistry]'")
            else:
                logger.warning(f"⚠️  Schema Registry client not available: {schema_registry_import_error}")
            logger.info("🔄 Falling back to JSON serialization")
            self.use_schema_registry = False
        else:
            try:
                logger.info("🔧 Initializing Schema Registry integration...")
                self.schema_registry = get_schema_registry()
                
                # Verify schema registry is working
                logger.info("🔍 Testing Schema Registry functionality...")
                test_serializer = self.schema_registry.get_serializer('support-tickets')
                if test_serializer:
                    logger.info("✅ Schema Registry initialized successfully - Avro serialization enabled")
                    
                    # Check schema attachments
                    self.schema_registry.check_schema_attachments()
                else:
                    logger.warning("⚠️  Schema Registry available but serializers not ready - falling back to JSON")
                    self.use_schema_registry = False
                    
            except Exception as e:
                logger.error(f"❌ Schema Registry initialization failed: {e}")
                logger.warning("🔄 Falling back to JSON serialization")
                self.use_schema_registry = False
        
        # String serializers for keys
        self.string_serializer = StringSerializer('utf_8')
        self.string_deserializer = StringDeserializer('utf_8')
        
        if self.jsonrpc_processor and self.use_jsonrpc:
            logger.info("📞 JSON-RPC 2.0 enabled for Kafka messaging")
        else:
            logger.info("📝 Using standard JSON for Kafka messaging")
        
        if self.use_schema_registry:
            logger.info("🔗 Avro serialization enabled via Schema Registry")
        else:
            logger.info("📝 Using JSON serialization")
        
        if not demo_mode:
            self._setup_kafka_config()
        else:
            logger.info("Running in demo mode - Kafka operations will be simulated")
    
    def _setup_kafka_config(self):
        # Get credentials from environment
        bootstrap_servers = os.getenv('CONFLUENT_BOOTSTRAP_SERVERS')
        api_key = os.getenv('CONFLUENT_API_KEY')
        api_secret = os.getenv('CONFLUENT_API_SECRET')
        
        # Validate credentials
        if not bootstrap_servers or not api_key or not api_secret:
            logger.error("Missing Confluent Cloud credentials")
            logger.error(f"Bootstrap servers: {'✓' if bootstrap_servers else '✗'}")
            logger.error(f"API key: {'✓' if api_key else '✗'}")
            logger.error(f"API secret: {'✓' if api_secret else '✗'}")
            self.demo_mode = True
            return
        
        # Check for placeholder values
        if (bootstrap_servers.startswith('your-') or 
            api_key.startswith('your-') or 
            api_secret.startswith('your-')):
            logger.error("Confluent credentials contain placeholder values")
            self.demo_mode = True
            return
        
        # Configurable timeouts via environment variables
        session_timeout = int(os.getenv('KAFKA_SESSION_TIMEOUT_MS', '60000'))  # Default 60s
        request_timeout = int(os.getenv('KAFKA_REQUEST_TIMEOUT_MS', '45000'))  # Default 45s
        socket_timeout = int(os.getenv('KAFKA_SOCKET_TIMEOUT_MS', '60000'))    # Default 60s
        
        logger.info(f"Kafka timeouts: session={session_timeout}ms, request={request_timeout}ms, socket={socket_timeout}ms")
        
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'sasl.mechanisms': 'PLAIN',
            'security.protocol': 'SASL_SSL',
            'sasl.username': api_key,
            'sasl.password': api_secret,
            'session.timeout.ms': session_timeout,
            'request.timeout.ms': request_timeout,
            'socket.timeout.ms': socket_timeout,
            'socket.keepalive.enable': True,
            'heartbeat.interval.ms': 3000,
        }
        
        # Producer config with extended timeouts and Stream Lineage visibility
        producer_config = {
            **self.config,
            'client.id': 'gradio-sentiment-producer',  # Visible in Stream Lineage
            'acks': 'all',
            'retries': 5,
            'retry.backoff.ms': 1000,
            'batch.size': 16384,
            'linger.ms': 10,
            'delivery.timeout.ms': int(os.getenv('KAFKA_DELIVERY_TIMEOUT_MS', '120000')),  # 2 min
            'message.timeout.ms': int(os.getenv('KAFKA_MESSAGE_TIMEOUT_MS', '300000')),   # 5 min
        }
        
        # Consumer config with Stream Lineage visibility
        consumer_config = {
            **self.config,
            'client.id': 'gradio-sentiment-consumer',  # Visible in Stream Lineage
            'group.id': 'gradio-sentiment-analyzer-group',  # Visible in Stream Lineage
            'auto.offset.reset': 'latest',
            'enable.auto.commit': True,
        }
        
        try:
            logger.info("Initializing Kafka clients...")
            logger.info(f"Bootstrap servers: {bootstrap_servers}")
            
            # Initialize clients
            self.admin_client = AdminClient(self.config)
            self.producer = Producer(producer_config)
            self.consumer = Consumer(consumer_config)
            
            # Test connection by listing topics
            metadata = self.admin_client.list_topics(timeout=10)
            logger.info(f"✅ Kafka client initialized successfully")
            logger.info(f"Connected to cluster with {len(metadata.topics)} existing topics")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kafka client: {e}")
            logger.error("Falling back to demo mode")
            self.admin_client = None
            self.producer = None
            self.consumer = None
            self.demo_mode = True
    
    def create_topics(self, topics: list):
        if self.demo_mode:
            logger.info(f"Demo mode: Would create topics {topics}")
            return True
        
        if self.admin_client is None:
            logger.error("Admin client not initialized")
            logger.debug(f"Debug: admin_client={self.admin_client}, type={type(self.admin_client)}")
            return False
        
        logger.debug(f"Debug: admin_client exists: {self.admin_client}, creating topics...")
        
        # First, check which topics already exist
        existing_topics = self.list_topics()
        topics_to_create = [topic for topic in topics if topic not in existing_topics]
        
        if not topics_to_create:
            logger.info(f"All topics already exist: {topics}")
            return True
        
        logger.info(f"Creating topics: {topics_to_create}")
        
        topic_list = []
        for topic in topics_to_create:
            # Use 3 partitions and replication factor 3 for production
            topic_list.append(NewTopic(
                topic, 
                num_partitions=3, 
                replication_factor=3,
                config={
                    'retention.ms': '604800000',  # 7 days
                    'cleanup.policy': 'delete'
                }
            ))
        
        try:
            fs = self.admin_client.create_topics(topic_list, validate_only=False)
            success = True
            for topic, f in fs.items():
                try:
                    f.result(timeout=30)  # Wait up to 30 seconds
                    logger.info(f"✅ Topic '{topic}' created successfully")
                except Exception as e:
                    if "TopicExistsError" in str(e) or "already exists" in str(e).lower():
                        logger.info(f"✅ Topic '{topic}' already exists")
                    else:
                        logger.error(f"❌ Failed to create topic '{topic}': {e}")
                        success = False
            return success
        except Exception as e:
            logger.error(f"❌ Failed to create topics: {e}")
            return False
    
    def list_topics(self):
        """List existing topics in the cluster"""
        if self.demo_mode:
            logger.debug("Demo mode: returning empty topic list")
            return []
        
        if self.admin_client is None:
            logger.error("Admin client not available for list_topics")
            logger.debug(f"Debug list_topics: admin_client={self.admin_client}, type={type(self.admin_client)}")
            return []
        
        try:
            logger.debug("Listing topics via admin client...")
            metadata = self.admin_client.list_topics(timeout=10)
            topics = list(metadata.topics.keys())
            logger.debug(f"Successfully listed {len(topics)} topics: {topics}")
            return topics
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            return []
    
    def describe_topics(self, topics: list):
        """Get detailed information about topics"""
        if self.demo_mode:
            logger.info(f"Demo mode: Would describe topics {topics}")
            return {}
        
        try:
            from confluent_kafka.admin import ConfigResource, ResourceType
            
            resources = [ConfigResource(ResourceType.TOPIC, topic) for topic in topics]
            fs = self.admin_client.describe_configs(resources)
            
            results = {}
            for resource, f in fs.items():
                try:
                    config = f.result()
                    results[resource.name] = config
                    logger.info(f"Topic '{resource.name}' configuration retrieved")
                except Exception as e:
                    logger.error(f"Failed to describe topic '{resource.name}': {e}")
            
            return results
        except Exception as e:
            logger.error(f"Failed to describe topics: {e}")
            return {}
    
    def send_message(self, topic: str, message: Dict, key: str = None, method: str = None):
        if self.demo_mode:
            logger.info(f"Demo mode: Would send to {topic}: {message}")
            return
        
        try:
            # Serialize message value
            if self.use_schema_registry and self.schema_registry:
                # Use Avro serialization with Schema Registry
                logger.debug(f"🔗 Attempting Avro serialization for topic: {topic}")
                serializer = self.schema_registry.get_serializer(topic)
                if serializer:
                    # Add timestamp if not present
                    if 'timestamp' not in message:
                        message['timestamp'] = int(datetime.now().timestamp() * 1000)
                    
                    logger.debug(f"📋 Message fields: {list(message.keys())}")
                    serialization_context = SerializationContext(topic, MessageField.VALUE)
                    
                    try:
                        serialized_value = serializer(message, serialization_context)
                        logger.info(f"✅ Message serialized using Avro for topic '{topic}' (size: {len(serialized_value)} bytes)")
                    except Exception as e:
                        logger.error(f"❌ Avro serialization failed for topic '{topic}': {e}")
                        logger.warning(f"🔄 Falling back to JSON serialization for this message")
                        serialized_value = json.dumps(message)
                else:
                    # Fallback to JSON if serializer not available
                    logger.warning(f"⚠️  No Avro serializer available for topic '{topic}' - using JSON fallback")
                    serialized_value = json.dumps(message)
            else:
                # JSON serialization (with optional JSON-RPC 2.0)
                if self.use_jsonrpc and self.jsonrpc_processor:
                    # Create JSON-RPC 2.0 request for structured messaging
                    rpc_method = method or f"kafka.{topic.replace('-', '_')}"
                    request = self.jsonrpc_processor.create_request(
                        method=rpc_method,
                        params=message,
                        request_id=message.get('ticket_id', key)
                    )
                    serialized_value = request.to_json()
                    logger.debug(f"📞 Sending JSON-RPC 2.0 message to {topic}: {rpc_method}")
                else:
                    # Standard JSON format
                    serialized_value = json.dumps(message)
                    logger.debug(f"📝 Sending standard JSON message to {topic}")
            
            # Serialize key
            serialized_key = self.string_serializer(key) if key else None
            
            self.producer.produce(
                topic,
                key=serialized_key,
                value=serialized_value,
                callback=self._delivery_callback
            )
            self.producer.flush()
            
        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
    
    def _delivery_callback(self, err, msg):
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.info(f'Message delivered to {msg.topic()} [{msg.partition()}]')
    
    def consume_messages(self, topics: list, callback: Callable[[Dict], None]):
        if self.demo_mode:
            logger.info(f"Demo mode: Would consume from topics {topics}")
            return
        
        try:
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
            
            while True:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f'Consumer error: {msg.error()}')
                        break
                
                try:
                    topic = msg.topic()
                    
                    # Deserialize message value
                    if self.use_schema_registry and self.schema_registry:
                        # Use Avro deserialization with Schema Registry
                        logger.debug(f"🔗 Attempting Avro deserialization for topic: {topic}")
                        deserializer = self.schema_registry.get_deserializer(topic)
                        if deserializer:
                            serialization_context = SerializationContext(topic, MessageField.VALUE)
                            
                            try:
                                message_data = deserializer(msg.value(), serialization_context)
                                logger.info(f"✅ Message deserialized using Avro from topic '{topic}' (fields: {list(message_data.keys()) if isinstance(message_data, dict) else 'N/A'})")
                            except Exception as e:
                                logger.error(f"❌ Avro deserialization failed for topic '{topic}': {e}")
                                logger.warning(f"🔄 Falling back to JSON deserialization for this message")
                                raw_message = msg.value().decode('utf-8')
                                message_data = json.loads(raw_message)
                        else:
                            # Fallback to JSON if deserializer not available
                            logger.warning(f"⚠️  No Avro deserializer available for topic '{topic}' - using JSON fallback")
                            raw_message = msg.value().decode('utf-8')
                            message_data = json.loads(raw_message)
                    else:
                        # JSON deserialization (with optional JSON-RPC 2.0)
                        raw_message = msg.value().decode('utf-8')
                        
                        # Try to parse as JSON-RPC 2.0 first if enabled
                        if self.use_jsonrpc and self.jsonrpc_processor:
                            try:
                                parsed = self.jsonrpc_processor.parse_request(raw_message)
                                if isinstance(parsed, JsonRpcRequest):
                                    # Extract params from JSON-RPC request
                                    message_data = parsed.params or {}
                                    # Add JSON-RPC metadata
                                    message_data['_jsonrpc'] = {
                                        'method': parsed.method,
                                        'id': parsed.id,
                                        'version': parsed.jsonrpc
                                    }
                                    logger.debug(f"📞 Processed JSON-RPC 2.0 message: {parsed.method}")
                                else:
                                    # Error response - log and skip
                                    logger.warning(f"Received JSON-RPC error: {parsed.to_json()}")
                                    continue
                            except Exception:
                                # Fallback to standard JSON parsing
                                message_data = json.loads(raw_message)
                                logger.debug(f"📝 Fallback to standard JSON parsing")
                        else:
                            # Standard JSON parsing
                            message_data = json.loads(raw_message)
                            logger.debug(f"📝 Processed standard JSON message")
                    
                    # Add message metadata
                    if isinstance(message_data, dict):
                        message_data['_kafka_metadata'] = {
                            'topic': topic,
                            'partition': msg.partition(),
                            'offset': msg.offset(),
                            'timestamp': msg.timestamp()[1] if msg.timestamp()[0] != -1 else None
                        }
                    
                    callback(message_data)
                    
                except Exception as e:
                    logger.error(f"Error processing message from {topic}: {e}")
                    if hasattr(msg, 'value') and msg.value():
                        try:
                            raw_val = msg.value().decode('utf-8')[:200]
                            logger.debug(f"Raw message: {raw_val}...")
                        except:
                            logger.debug("Could not decode message for debugging")
        
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            if self.consumer:
                self.consumer.close()

class DemoMessageGenerator:
    def __init__(self):
        self.demo_messages = [
            {
                "ticket_id": "T001",
                "customer_id": "C001",
                "message": "I am absolutely furious! Your service is terrible and I want my money back immediately!",
                "timestamp": datetime.now().isoformat()
            },
            {
                "ticket_id": "T002", 
                "customer_id": "C002",
                "message": "Hi, I'm having trouble logging into my account. Could you please help me?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "ticket_id": "T003",
                "customer_id": "C003", 
                "message": "This is unacceptable! I've been waiting for hours and no one has responded. I'm canceling my subscription!",
                "timestamp": datetime.now().isoformat()
            },
            {
                "ticket_id": "T004",
                "customer_id": "C004",
                "message": "Thank you for the quick response yesterday. The issue has been resolved.",
                "timestamp": datetime.now().isoformat()
            },
            {
                "ticket_id": "T005",
                "customer_id": "C005",
                "message": "URGENT: Our production system is down and we need immediate assistance!",
                "timestamp": datetime.now().isoformat()
            }
        ]
        self.current_index = 0
    
    def get_next_message(self) -> Dict:
        message = self.demo_messages[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.demo_messages)
        
        # Update timestamp to current time
        message["timestamp"] = datetime.now().isoformat()
        return message