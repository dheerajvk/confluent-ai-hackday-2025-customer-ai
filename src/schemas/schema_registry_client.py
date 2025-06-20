"""
Schema Registry Client for Confluent Cloud
Manages Avro schema registration and retrieval for Kafka topics
"""
import os
import json
import logging
from typing import Dict, Optional
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class CustomerServiceSchemaRegistry:
    """Schema Registry client for customer service Kafka topics"""
    
    def __init__(self):
        """Initialize Schema Registry client with Confluent Cloud configuration"""
        logger.info("🔧 Initializing Schema Registry client...")
        
        self.schema_registry_url = os.getenv('SCHEMA_REGISTRY_URL')
        self.schema_registry_api_key = os.getenv('SCHEMA_REGISTRY_API_KEY')
        self.schema_registry_api_secret = os.getenv('SCHEMA_REGISTRY_API_SECRET')
        
        logger.info(f"📍 Schema Registry URL: {self.schema_registry_url}")
        logger.info(f"🔑 API Key configured: {'✓' if self.schema_registry_api_key else '✗'}")
        logger.info(f"🗝️  API Secret configured: {'✓' if self.schema_registry_api_secret else '✗'}")
        
        if not all([self.schema_registry_url, self.schema_registry_api_key, self.schema_registry_api_secret]):
            logger.error("❌ Schema Registry configuration missing in environment variables")
            missing = []
            if not self.schema_registry_url: missing.append("SCHEMA_REGISTRY_URL")
            if not self.schema_registry_api_key: missing.append("SCHEMA_REGISTRY_API_KEY")
            if not self.schema_registry_api_secret: missing.append("SCHEMA_REGISTRY_API_SECRET")
            logger.error(f"Missing variables: {', '.join(missing)}")
            raise ValueError("Schema Registry configuration missing in environment variables")
        
        # Schema Registry client configuration
        schema_registry_conf = {
            'url': self.schema_registry_url,
            'basic.auth.user.info': f'{self.schema_registry_api_key}:{self.schema_registry_api_secret}'
        }
        
        logger.info("🔌 Connecting to Schema Registry...")
        try:
            self.schema_registry_client = SchemaRegistryClient(schema_registry_conf)
            
            # Test connection by trying to get subjects
            logger.info("🧪 Testing Schema Registry connection...")
            subjects = self.schema_registry_client.get_subjects()
            logger.info(f"✅ Schema Registry connection successful! Found {len(subjects)} existing subjects: {subjects}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Failed to connect to Schema Registry: {e}")
            
            # Provide helpful error messages based on the error type
            if "nodename nor servname provided" in error_msg or "Unknown host" in error_msg:
                logger.error("🌐 Network Error: Schema Registry hostname could not be resolved")
                logger.error(f"   URL: {self.schema_registry_url}")
                logger.error("   This could indicate:")
                logger.error("   1. Invalid Schema Registry URL")
                logger.error("   2. Schema Registry not enabled in Confluent Cloud")
                logger.error("   3. Incorrect region in the URL")
                logger.error("   4. Network connectivity issues")
                logger.info("💡 To find the correct Schema Registry URL:")
                logger.info("   1. Go to Confluent Cloud → Your Cluster")
                logger.info("   2. Click 'Schema Registry' tab")
                logger.info("   3. Enable Schema Registry if not already enabled")
                logger.info("   4. Copy the correct endpoint URL")
            elif "401" in error_msg or "Unauthorized" in error_msg:
                logger.error("🔑 Authentication Error: Invalid Schema Registry credentials")
                logger.error("   Check SCHEMA_REGISTRY_API_KEY and SCHEMA_REGISTRY_API_SECRET")
            elif "403" in error_msg or "Forbidden" in error_msg:
                logger.error("🚫 Permission Error: Schema Registry access denied")
                logger.error("   Check if your API key has Schema Registry permissions")
            
            raise
        
        # Load schemas
        logger.info("📄 Loading Avro schemas from files...")
        self.schemas = self._load_schemas()
        
        # Initialize serializers and deserializers
        logger.info("🔄 Creating serializers and deserializers...")
        self.serializers = self._create_serializers()
        self.deserializers = self._create_deserializers()
        
        logger.info("✅ Schema Registry client initialized successfully")
    
    def _load_schemas(self) -> Dict[str, str]:
        """Load Avro schemas from files"""
        schemas = {}
        schema_dir = os.path.join(os.path.dirname(__file__))
        
        schema_files = {
            'support-tickets': 'support_ticket_schema.avsc',
            'processed-tickets': 'processed_ticket_schema.avsc',
            'ai-responses': 'ai_response_schema.avsc'
        }
        
        logger.info(f"📂 Schema directory: {schema_dir}")
        
        for topic, filename in schema_files.items():
            schema_path = os.path.join(schema_dir, filename)
            logger.info(f"📄 Loading schema for topic '{topic}' from: {filename}")
            
            try:
                with open(schema_path, 'r') as f:
                    schema_content = f.read()
                    schemas[topic] = schema_content
                    
                # Parse to validate JSON
                schema_json = json.loads(schema_content)
                logger.info(f"✅ Schema loaded for topic '{topic}': {schema_json.get('name', 'Unknown')} (type: {schema_json.get('type', 'Unknown')})")
                logger.debug(f"   Fields count: {len(schema_json.get('fields', []))}")
                
            except FileNotFoundError:
                logger.error(f"❌ Schema file not found: {schema_path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in schema file {filename}: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ Error loading schema file {filename}: {e}")
                raise
        
        logger.info(f"📄 Successfully loaded {len(schemas)} schemas")
        return schemas
    
    def _create_serializers(self) -> Dict[str, AvroSerializer]:
        """Create Avro serializers for each topic"""
        serializers = {}
        
        for topic in self.schemas.keys():
            logger.info(f"🔄 Creating Avro serializer for topic: {topic}")
            try:
                if topic == 'support-tickets':
                    serializer = AvroSerializer(
                        self.schema_registry_client,
                        self.schemas[topic],
                        self._support_ticket_to_dict
                    )
                elif topic == 'processed-tickets':
                    serializer = AvroSerializer(
                        self.schema_registry_client,
                        self.schemas[topic],
                        self._processed_ticket_to_dict
                    )
                elif topic == 'ai-responses':
                    serializer = AvroSerializer(
                        self.schema_registry_client,
                        self.schemas[topic],
                        self._ai_response_to_dict
                    )
                else:
                    logger.warning(f"⚠️  Unknown topic: {topic}, skipping serializer creation")
                    continue
                
                serializers[topic] = serializer
                logger.info(f"✅ Serializer created for topic: {topic}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create serializer for topic '{topic}': {e}")
                raise
        
        logger.info(f"🔄 Successfully created {len(serializers)} serializers")
        return serializers
    
    def _create_deserializers(self) -> Dict[str, AvroDeserializer]:
        """Create Avro deserializers for each topic"""
        deserializers = {}
        
        for topic in self.schemas.keys():
            logger.info(f"🔄 Creating Avro deserializer for topic: {topic}")
            try:
                if topic == 'support-tickets':
                    deserializer = AvroDeserializer(
                        self.schema_registry_client,
                        self.schemas[topic],
                        self._dict_to_support_ticket
                    )
                elif topic == 'processed-tickets':
                    deserializer = AvroDeserializer(
                        self.schema_registry_client,
                        self.schemas[topic],
                        self._dict_to_processed_ticket
                    )
                elif topic == 'ai-responses':
                    deserializer = AvroDeserializer(
                        self.schema_registry_client,
                        self.schemas[topic],
                        self._dict_to_ai_response
                    )
                else:
                    logger.warning(f"⚠️  Unknown topic: {topic}, skipping deserializer creation")
                    continue
                
                deserializers[topic] = deserializer
                logger.info(f"✅ Deserializer created for topic: {topic}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create deserializer for topic '{topic}': {e}")
                raise
        
        logger.info(f"🔄 Successfully created {len(deserializers)} deserializers")
        return deserializers
    
    def get_serializer(self, topic: str) -> Optional[AvroSerializer]:
        """Get serializer for a specific topic"""
        return self.serializers.get(topic)
    
    def get_deserializer(self, topic: str) -> Optional[AvroDeserializer]:
        """Get deserializer for a specific topic"""
        return self.deserializers.get(topic)
    
    # Conversion functions for serialization
    def _support_ticket_to_dict(self, ticket, ctx):
        """Convert support ticket object to dict for Avro serialization"""
        if isinstance(ticket, dict):
            return ticket
        
        # Handle object conversion
        return {
            'ticket_id': getattr(ticket, 'ticket_id', ''),
            'customer_id': getattr(ticket, 'customer_id', ''),
            'subject': getattr(ticket, 'subject', ''),
            'message': getattr(ticket, 'message', ''),
            'priority': getattr(ticket, 'priority', 'MEDIUM'),
            'category': getattr(ticket, 'category', None),
            'timestamp': getattr(ticket, 'timestamp', 0),
            'metadata': getattr(ticket, 'metadata', {})
        }
    
    def _processed_ticket_to_dict(self, ticket, ctx):
        """Convert processed ticket object to dict for Avro serialization"""
        if isinstance(ticket, dict):
            return ticket
        
        return {
            'ticket_id': getattr(ticket, 'ticket_id', ''),
            'customer_id': getattr(ticket, 'customer_id', ''),
            'subject': getattr(ticket, 'subject', ''),
            'message': getattr(ticket, 'message', ''),
            'priority': getattr(ticket, 'priority', 'MEDIUM'),
            'category': getattr(ticket, 'category', None),
            'sentiment_score': getattr(ticket, 'sentiment_score', 0.0),
            'sentiment_label': getattr(ticket, 'sentiment_label', 'NEUTRAL'),
            'urgency_score': getattr(ticket, 'urgency_score', 0.0),
            'keywords': getattr(ticket, 'keywords', []),
            'processing_timestamp': getattr(ticket, 'processing_timestamp', 0),
            'original_timestamp': getattr(ticket, 'original_timestamp', 0),
            'processing_metadata': getattr(ticket, 'processing_metadata', {})
        }
    
    def _ai_response_to_dict(self, response, ctx):
        """Convert AI response object to dict for Avro serialization"""
        if isinstance(response, dict):
            return response
        
        return {
            'ticket_id': getattr(response, 'ticket_id', ''),
            'customer_id': getattr(response, 'customer_id', ''),
            'response_type': getattr(response, 'response_type', 'AUTO_RESPONSE'),
            'response_content': getattr(response, 'response_content', None),
            'confidence_score': getattr(response, 'confidence_score', 0.0),
            'escalation_required': getattr(response, 'escalation_required', False),
            'escalation_reason': getattr(response, 'escalation_reason', None),
            'suggested_department': getattr(response, 'suggested_department', None),
            'priority_adjustment': getattr(response, 'priority_adjustment', None),
            'tags': getattr(response, 'tags', []),
            'generated_timestamp': getattr(response, 'generated_timestamp', 0),
            'model_version': getattr(response, 'model_version', ''),
            'response_metadata': getattr(response, 'response_metadata', {})
        }
    
    # Conversion functions for deserialization
    def _dict_to_support_ticket(self, data, ctx):
        """Convert dict to support ticket object after Avro deserialization"""
        return data  # Return as dict for now, can be converted to object if needed
    
    def _dict_to_processed_ticket(self, data, ctx):
        """Convert dict to processed ticket object after Avro deserialization"""
        return data  # Return as dict for now, can be converted to object if needed
    
    def _dict_to_ai_response(self, data, ctx):
        """Convert dict to AI response object after Avro deserialization"""
        return data  # Return as dict for now, can be converted to object if needed
    
    def register_schema(self, topic: str, schema_str: str) -> int:
        """Register a schema for a specific topic"""
        subject = f"{topic}-value"
        logger.info(f"📝 Registering schema for topic '{topic}' with subject '{subject}'")
        
        try:
            # Parse schema to get details
            schema_json = json.loads(schema_str)
            schema_name = schema_json.get('name', 'Unknown')
            schema_type = schema_json.get('type', 'Unknown')
            field_count = len(schema_json.get('fields', []))
            
            logger.info(f"📋 Schema details: name='{schema_name}', type='{schema_type}', fields={field_count}")
            
            # Check if schema already exists
            try:
                existing_schema = self.schema_registry_client.get_latest_version(subject)
                logger.info(f"🔍 Found existing schema for subject '{subject}' (version {existing_schema.version}, ID {existing_schema.schema_id})")
                
                # Check if it's the same schema
                if existing_schema.schema.schema_str.strip() == schema_str.strip():
                    logger.info(f"✅ Schema for topic '{topic}' already registered with same content (ID: {existing_schema.schema_id})")
                    return existing_schema.schema_id
                else:
                    logger.info(f"🔄 Schema content differs, registering new version...")
                    
            except Exception as e:
                logger.info(f"ℹ️  No existing schema found for subject '{subject}': {e}")
            
            # Register the schema
            logger.info(f"📤 Sending schema registration request to Schema Registry...")
            schema_id = self.schema_registry_client.register_schema(subject, schema_str)
            
            # Verify registration
            try:
                registered_schema = self.schema_registry_client.get_schema(schema_id)
                logger.info(f"✅ Schema successfully registered for topic '{topic}':")
                logger.info(f"   📋 Subject: {subject}")
                logger.info(f"   🆔 Schema ID: {schema_id}")
                logger.info(f"   📝 Schema name: {schema_name}")
                logger.info(f"   🔢 Fields: {field_count}")
                
                # Get the latest version to confirm it's active
                latest = self.schema_registry_client.get_latest_version(subject)
                logger.info(f"   📈 Version: {latest.version}")
                logger.info(f"   ✅ Status: Active and ready for use")
                
            except Exception as e:
                logger.warning(f"⚠️  Could not verify schema registration: {e}")
            
            return schema_id
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON schema for topic '{topic}': {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to register schema for topic '{topic}': {e}")
            logger.error(f"   Subject: {subject}")
            logger.error(f"   Error type: {type(e).__name__}")
            raise
    
    def get_latest_schema(self, topic: str) -> Optional[str]:
        """Get the latest schema for a topic"""
        try:
            subject = f"{topic}-value"
            schema = self.schema_registry_client.get_latest_version(subject)
            return schema.schema.schema_str
        except Exception as e:
            logger.error(f"Failed to get latest schema for topic {topic}: {e}")
            return None
    
    def register_all_schemas(self):
        """Register all schemas for the topics"""
        logger.info("🚀 Starting bulk schema registration for all topics...")
        logger.info(f"📊 Total schemas to register: {len(self.schemas)}")
        
        success_count = 0
        failure_count = 0
        
        for topic, schema_str in self.schemas.items():
            try:
                logger.info(f"📝 Processing schema registration for topic: {topic}")
                schema_id = self.register_schema(topic, schema_str)
                success_count += 1
                logger.info(f"✅ Successfully registered schema for '{topic}' (ID: {schema_id})")
                
            except Exception as e:
                failure_count += 1
                logger.error(f"❌ Failed to register schema for '{topic}': {e}")
                logger.error(f"   This will prevent Avro serialization for topic '{topic}'")
        
        # Summary
        logger.info("📊 Schema registration summary:")
        logger.info(f"   ✅ Successful: {success_count}/{len(self.schemas)}")
        logger.info(f"   ❌ Failed: {failure_count}/{len(self.schemas)}")
        
        if failure_count > 0:
            logger.warning(f"⚠️  {failure_count} schema(s) failed to register. Topics with failed schemas will fall back to JSON serialization.")
        else:
            logger.info("🎉 All schemas registered successfully! Avro serialization is ready for all topics.")
        
        # Verify all registered schemas
        self._verify_all_schemas()
    
    def _verify_all_schemas(self):
        """Verify that all schemas are properly registered and accessible"""
        logger.info("🔍 Verifying all registered schemas...")
        
        try:
            # Get all subjects from Schema Registry
            all_subjects = self.schema_registry_client.get_subjects()
            logger.info(f"📋 Found {len(all_subjects)} total subjects in Schema Registry: {all_subjects}")
            
            # Check each topic
            for topic in self.schemas.keys():
                subject = f"{topic}-value"
                logger.info(f"🔍 Verifying schema for topic '{topic}' (subject: '{subject}')...")
                
                if subject in all_subjects:
                    try:
                        latest_version = self.schema_registry_client.get_latest_version(subject)
                        logger.info(f"✅ Schema found for '{topic}':")
                        logger.info(f"   📋 Subject: {subject}")
                        logger.info(f"   🆔 Schema ID: {latest_version.schema_id}")
                        logger.info(f"   📈 Version: {latest_version.version}")
                        
                        # Parse schema details
                        schema_json = json.loads(latest_version.schema.schema_str)
                        schema_name = schema_json.get('name', 'Unknown')
                        field_count = len(schema_json.get('fields', []))
                        logger.info(f"   📝 Schema name: {schema_name}")
                        logger.info(f"   🔢 Field count: {field_count}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error retrieving schema details for '{topic}': {e}")
                else:
                    logger.error(f"❌ Schema not found for topic '{topic}' (subject: '{subject}')")
            
            # Check for data contracts (compatibility settings)
            logger.info("🔍 Checking compatibility settings (data contracts)...")
            for topic in self.schemas.keys():
                subject = f"{topic}-value"
                try:
                    # Get compatibility level for the subject
                    compatibility = self.schema_registry_client.get_compatibility(subject)
                    logger.info(f"📋 Topic '{topic}' compatibility: {compatibility}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not get compatibility for '{topic}': {e}")
            
            logger.info("✅ Schema verification completed")
            
        except Exception as e:
            logger.error(f"❌ Error during schema verification: {e}")
    
    def check_schema_attachments(self):
        """Check if schemas are properly attached to topics"""
        logger.info("🔗 Checking schema attachments to Kafka topics...")
        
        for topic in self.schemas.keys():
            subject = f"{topic}-value"
            logger.info(f"🔍 Checking attachment for topic '{topic}'...")
            
            try:
                # Check if subject exists
                latest_version = self.schema_registry_client.get_latest_version(subject)
                
                # Try to get/create serializer to test attachment
                serializer = self.get_serializer(topic)
                if serializer:
                    logger.info(f"✅ Schema properly attached to topic '{topic}' - Avro serialization ready")
                else:
                    logger.error(f"❌ Schema not attached to topic '{topic}' - serializer not available")
                    
            except Exception as e:
                logger.error(f"❌ Schema attachment check failed for topic '{topic}': {e}")


# Global instance
schema_registry = None

def get_schema_registry():
    """Get singleton instance of schema registry"""
    global schema_registry
    if schema_registry is None:
        try:
            schema_registry = CustomerServiceSchemaRegistry()
        except Exception as e:
            logger.warning(f"⚠️  Real Schema Registry unavailable: {e}")
            logger.info("🎭 Falling back to Mock Schema Registry for development/testing")
            
            # Import and use mock schema registry
            try:
                from .mock_schema_registry import get_mock_schema_registry
                schema_registry = get_mock_schema_registry()
                logger.info("✅ Mock Schema Registry initialized successfully")
            except Exception as mock_error:
                logger.error(f"❌ Mock Schema Registry also failed: {mock_error}")
                raise
    
    return schema_registry