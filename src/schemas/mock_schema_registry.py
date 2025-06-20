"""
Mock Schema Registry for development and testing
Provides fallback functionality when real Schema Registry is unavailable
"""
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class MockSchemaRegistryClient:
    """Mock Schema Registry client for testing and development"""
    
    def __init__(self):
        self.schemas = {}
        self.next_id = 1
        logger.info("🎭 Mock Schema Registry client initialized")
    
    def get_subjects(self):
        """Return mock subjects"""
        return list(self.schemas.keys())
    
    def register_schema(self, subject: str, schema_str: str) -> int:
        """Mock schema registration"""
        schema_id = self.next_id
        self.schemas[subject] = {
            'id': schema_id,
            'schema': schema_str,
            'version': 1
        }
        self.next_id += 1
        logger.info(f"🎭 Mock registered schema for {subject} with ID {schema_id}")
        return schema_id
    
    def get_schema(self, schema_id: int):
        """Mock get schema by ID"""
        for subject, data in self.schemas.items():
            if data['id'] == schema_id:
                return type('Schema', (), {'schema_str': data['schema']})()
        raise Exception(f"Schema ID {schema_id} not found")
    
    def get_latest_version(self, subject: str):
        """Mock get latest version"""
        if subject in self.schemas:
            data = self.schemas[subject]
            return type('Version', (), {
                'schema_id': data['id'],
                'version': data['version'],
                'schema': type('Schema', (), {'schema_str': data['schema']})()
            })()
        raise Exception(f"Subject {subject} not found")
    
    def get_compatibility(self, subject: str):
        """Mock compatibility check"""
        return "BACKWARD"

class MockAvroSerializer:
    """Mock Avro serializer for testing"""
    
    def __init__(self, schema_registry_client, schema_str, to_dict_fn):
        self.schema_str = schema_str
        self.to_dict_fn = to_dict_fn
        self.schema = json.loads(schema_str)
        logger.debug(f"🎭 Mock Avro serializer created for {self.schema.get('name', 'Unknown')}")
    
    def __call__(self, obj, ctx):
        """Mock serialization - just return JSON bytes"""
        data = self.to_dict_fn(obj, ctx) if self.to_dict_fn else obj
        # Simulate Avro binary format with a prefix
        json_data = json.dumps(data)
        return b'\x00\x00\x00\x00\x01' + json_data.encode('utf-8')  # Magic bytes + JSON

class MockAvroDeserializer:
    """Mock Avro deserializer for testing"""
    
    def __init__(self, schema_registry_client, schema_str, from_dict_fn):
        self.schema_str = schema_str
        self.from_dict_fn = from_dict_fn
        self.schema = json.loads(schema_str)
        logger.debug(f"🎭 Mock Avro deserializer created for {self.schema.get('name', 'Unknown')}")
    
    def __call__(self, data, ctx):
        """Mock deserialization - parse JSON from bytes"""
        # Remove mock magic bytes and parse JSON
        if data.startswith(b'\x00\x00\x00\x00\x01'):
            json_data = data[5:].decode('utf-8')
            parsed = json.loads(json_data)
            return self.from_dict_fn(parsed, ctx) if self.from_dict_fn else parsed
        else:
            # Fallback for non-mock data
            return json.loads(data.decode('utf-8'))

class MockCustomerServiceSchemaRegistry:
    """Mock version of CustomerServiceSchemaRegistry"""
    
    def __init__(self):
        logger.info("🎭 Initializing Mock Schema Registry for testing...")
        
        self.schema_registry_client = MockSchemaRegistryClient()
        
        # Load schemas from files
        self.schemas = self._load_schemas()
        
        # Create mock serializers and deserializers
        self.serializers = self._create_mock_serializers()
        self.deserializers = self._create_mock_deserializers()
        
        logger.info("✅ Mock Schema Registry initialized - JSON serialization with Avro simulation")
    
    def _load_schemas(self) -> Dict[str, str]:
        """Load schemas from files (same as real implementation)"""
        import os
        schemas = {}
        schema_dir = os.path.join(os.path.dirname(__file__))
        
        schema_files = {
            'support-tickets': 'support_ticket_schema.avsc',
            'processed-tickets': 'processed_ticket_schema.avsc',
            'ai-responses': 'ai_response_schema.avsc'
        }
        
        for topic, filename in schema_files.items():
            schema_path = os.path.join(schema_dir, filename)
            try:
                with open(schema_path, 'r') as f:
                    schemas[topic] = f.read()
                logger.info(f"🎭 Loaded mock schema for topic: {topic}")
            except FileNotFoundError:
                logger.warning(f"⚠️  Schema file not found: {schema_path}")
        
        return schemas
    
    def _create_mock_serializers(self) -> Dict[str, MockAvroSerializer]:
        """Create mock serializers"""
        serializers = {}
        
        for topic in self.schemas.keys():
            if topic == 'support-tickets':
                to_dict_fn = self._support_ticket_to_dict
            elif topic == 'processed-tickets':
                to_dict_fn = self._processed_ticket_to_dict
            elif topic == 'ai-responses':
                to_dict_fn = self._ai_response_to_dict
            else:
                to_dict_fn = None
            
            serializers[topic] = MockAvroSerializer(
                self.schema_registry_client,
                self.schemas[topic],
                to_dict_fn
            )
        
        return serializers
    
    def _create_mock_deserializers(self) -> Dict[str, MockAvroDeserializer]:
        """Create mock deserializers"""
        deserializers = {}
        
        for topic in self.schemas.keys():
            if topic == 'support-tickets':
                from_dict_fn = self._dict_to_support_ticket
            elif topic == 'processed-tickets':
                from_dict_fn = self._dict_to_processed_ticket
            elif topic == 'ai-responses':
                from_dict_fn = self._dict_to_ai_response
            else:
                from_dict_fn = None
            
            deserializers[topic] = MockAvroDeserializer(
                self.schema_registry_client,
                self.schemas[topic],
                from_dict_fn
            )
        
        return deserializers
    
    def get_serializer(self, topic: str) -> Optional[MockAvroSerializer]:
        """Get mock serializer for a topic"""
        return self.serializers.get(topic)
    
    def get_deserializer(self, topic: str) -> Optional[MockAvroDeserializer]:
        """Get mock deserializer for a topic"""
        return self.deserializers.get(topic)
    
    def register_all_schemas(self):
        """Mock schema registration"""
        logger.info("🎭 Mock registering all schemas...")
        for topic, schema_str in self.schemas.items():
            subject = f"{topic}-value"
            schema_id = self.schema_registry_client.register_schema(subject, schema_str)
            logger.info(f"🎭 Mock registered schema for {topic} with ID {schema_id}")
        logger.info("✅ Mock schema registration completed")
    
    def check_schema_attachments(self):
        """Mock schema attachment check"""
        logger.info("🎭 Mock checking schema attachments...")
        for topic in self.schemas.keys():
            logger.info(f"✅ Mock schema attached to topic '{topic}' - simulation ready")
    
    def get_latest_schema(self, topic: str) -> Optional[str]:
        """Mock get latest schema for a topic"""
        if topic in self.schemas:
            return self.schemas[topic]
        return None
    
    def register_schema(self, topic: str, schema_str: str) -> int:
        """Mock register a single schema"""
        subject = f"{topic}-value"
        return self.schema_registry_client.register_schema(subject, schema_str)
    
    # Conversion functions (same as real implementation)
    def _support_ticket_to_dict(self, ticket, ctx):
        if isinstance(ticket, dict):
            return ticket
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
    
    def _dict_to_support_ticket(self, data, ctx):
        return data
    
    def _dict_to_processed_ticket(self, data, ctx):
        return data
    
    def _dict_to_ai_response(self, data, ctx):
        return data

# Mock version of the get_schema_registry function
def get_mock_schema_registry() -> MockCustomerServiceSchemaRegistry:
    """Get mock schema registry instance"""
    return MockCustomerServiceSchemaRegistry()