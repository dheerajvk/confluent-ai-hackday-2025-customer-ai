"""
JSON-RPC 2.0 Implementation for Confluent AI Support Optimizer

This module provides JSON-RPC 2.0 compliant request/response handling
for inter-service communication and API calls.

JSON-RPC 2.0 Specification: https://www.jsonrpc.org/specification
"""
import json
import uuid
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 Request object"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Union[List, Dict]] = None
    id: Optional[Union[str, int]] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 Response object"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        response = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            response["id"] = self.id
        if self.error is not None:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

@dataclass  
class JsonRpcError:
    """JSON-RPC 2.0 Error object"""
    code: int
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        error = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error

class JsonRpcErrorCodes:
    """Standard JSON-RPC 2.0 error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32099
    SERVER_ERROR_END = -32000

class JsonRpcProcessor:
    """JSON-RPC 2.0 Request/Response processor"""
    
    def __init__(self):
        self.methods = {}
        self.middleware = []
    
    def register_method(self, name: str, method: callable):
        """Register a method that can be called via JSON-RPC"""
        self.methods[name] = method
        logger.info(f"📞 Registered JSON-RPC method: {name}")
    
    def add_middleware(self, middleware: callable):
        """Add middleware function that processes requests/responses"""
        self.middleware.append(middleware)
        logger.info(f"🔗 Added JSON-RPC middleware: {middleware.__name__}")
    
    def create_request(self, method: str, params: Optional[Union[List, Dict]] = None, 
                      request_id: Optional[Union[str, int]] = None) -> JsonRpcRequest:
        """Create a JSON-RPC 2.0 request"""
        return JsonRpcRequest(method=method, params=params, id=request_id)
    
    def create_success_response(self, result: Any, request_id: Optional[Union[str, int]] = None) -> JsonRpcResponse:
        """Create a successful JSON-RPC 2.0 response"""
        return JsonRpcResponse(result=result, id=request_id)
    
    def create_error_response(self, error_code: int, error_message: str, 
                             error_data: Optional[Any] = None,
                             request_id: Optional[Union[str, int]] = None) -> JsonRpcResponse:
        """Create an error JSON-RPC 2.0 response"""
        error = JsonRpcError(code=error_code, message=error_message, data=error_data)
        return JsonRpcResponse(error=error.to_dict(), id=request_id)
    
    def parse_request(self, json_string: str) -> Union[JsonRpcRequest, JsonRpcResponse]:
        """Parse JSON-RPC 2.0 request from JSON string"""
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.error(f"JSON-RPC parse error: {e}")
            return self.create_error_response(
                JsonRpcErrorCodes.PARSE_ERROR,
                "Parse error",
                str(e)
            )
        
        # Validate JSON-RPC 2.0 format
        if not isinstance(data, dict):
            return self.create_error_response(
                JsonRpcErrorCodes.INVALID_REQUEST,
                "Invalid Request - must be JSON object"
            )
        
        if data.get("jsonrpc") != "2.0":
            return self.create_error_response(
                JsonRpcErrorCodes.INVALID_REQUEST,
                "Invalid Request - missing or invalid jsonrpc version"
            )
        
        if "method" not in data:
            return self.create_error_response(
                JsonRpcErrorCodes.INVALID_REQUEST,
                "Invalid Request - missing method"
            )
        
        # Create request object
        try:
            request = JsonRpcRequest(
                method=data["method"],
                params=data.get("params"),
                id=data.get("id")
            )
            return request
        except Exception as e:
            logger.error(f"JSON-RPC request creation error: {e}")
            return self.create_error_response(
                JsonRpcErrorCodes.INVALID_REQUEST,
                f"Invalid Request - {str(e)}"
            )
    
    def process_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Process a JSON-RPC 2.0 request and return response"""
        try:
            # Apply middleware
            for middleware in self.middleware:
                try:
                    request = middleware(request)
                except Exception as e:
                    logger.error(f"Middleware error: {e}")
                    return self.create_error_response(
                        JsonRpcErrorCodes.INTERNAL_ERROR,
                        f"Middleware error: {str(e)}",
                        request_id=request.id
                    )
            
            # Check if method exists
            if request.method not in self.methods:
                logger.warning(f"JSON-RPC method not found: {request.method}")
                return self.create_error_response(
                    JsonRpcErrorCodes.METHOD_NOT_FOUND,
                    f"Method not found: {request.method}",
                    request_id=request.id
                )
            
            # Get method
            method = self.methods[request.method]
            
            # Call method with parameters
            try:
                if request.params is None:
                    result = method()
                elif isinstance(request.params, list):
                    result = method(*request.params)
                elif isinstance(request.params, dict):
                    result = method(**request.params)
                else:
                    raise ValueError("Params must be array or object")
                
                logger.info(f"✅ JSON-RPC method '{request.method}' executed successfully")
                return self.create_success_response(result, request.id)
                
            except TypeError as e:
                logger.error(f"JSON-RPC invalid params for {request.method}: {e}")
                return self.create_error_response(
                    JsonRpcErrorCodes.INVALID_PARAMS,
                    f"Invalid params: {str(e)}",
                    request_id=request.id
                )
            except Exception as e:
                logger.error(f"JSON-RPC method execution error: {e}")
                return self.create_error_response(
                    JsonRpcErrorCodes.INTERNAL_ERROR,
                    f"Method execution error: {str(e)}",
                    request_id=request.id
                )
                
        except Exception as e:
            logger.error(f"JSON-RPC processing error: {e}")
            return self.create_error_response(
                JsonRpcErrorCodes.INTERNAL_ERROR,
                f"Internal error: {str(e)}",
                request_id=getattr(request, 'id', None)
            )
    
    def handle_json_string(self, json_string: str) -> str:
        """Handle JSON-RPC request from JSON string and return JSON response"""
        # Parse request
        parsed = self.parse_request(json_string)
        
        # If parsing failed, return error response
        if isinstance(parsed, JsonRpcResponse):
            return parsed.to_json()
        
        # Process request
        response = self.process_request(parsed)
        return response.to_json()

class TicketProcessingRpcService:
    """JSON-RPC 2.0 service for ticket processing operations"""
    
    def __init__(self):
        self.processor = JsonRpcProcessor()
        self._register_methods()
    
    def _register_methods(self):
        """Register all available RPC methods"""
        self.processor.register_method("sentiment.analyze", self.analyze_sentiment)
        self.processor.register_method("ticket.process", self.process_ticket)
        self.processor.register_method("ai.generate_response", self.generate_ai_response)
        self.processor.register_method("escalation.check", self.check_escalation)
        self.processor.register_method("system.health", self.system_health)
        self.processor.register_method("system.version", self.system_version)
    
    def analyze_sentiment(self, message: str) -> Dict:
        """Analyze sentiment of a message"""
        try:
            from .sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            result = analyzer.analyze(message)
            
            return {
                "sentiment": result["sentiment"],
                "polarity": result["polarity"],
                "subjectivity": result["subjectivity"],
                "confidence": result.get("confidence", 0.8),
                "timestamp": datetime.now().isoformat(),
                "service": "sentiment_analyzer"
            }
        except Exception as e:
            raise Exception(f"Sentiment analysis failed: {str(e)}")
    
    def process_ticket(self, ticket_data: Dict) -> Dict:
        """Process a complete ticket through the pipeline"""
        try:
            from .sentiment import TicketProcessor
            processor = TicketProcessor()
            result = processor.process_ticket(ticket_data)
            
            return {
                **result,
                "processed_at": datetime.now().isoformat(),
                "service": "ticket_processor"
            }
        except Exception as e:
            raise Exception(f"Ticket processing failed: {str(e)}")
    
    def generate_ai_response(self, ticket_data: Dict, demo_mode: bool = True) -> Dict:
        """Generate AI response for a ticket"""
        try:
            from ..ai.response_generator import AIResponseGenerator
            generator = AIResponseGenerator(demo_mode=demo_mode)
            result = generator.generate_response(ticket_data)
            
            return {
                **result,
                "generated_at": datetime.now().isoformat(),
                "service": "ai_response_generator"
            }
        except Exception as e:
            raise Exception(f"AI response generation failed: {str(e)}")
    
    def check_escalation(self, ticket_data: Dict) -> Dict:
        """Check if a ticket needs escalation"""
        try:
            sentiment = ticket_data.get("sentiment", "neutral")
            polarity = ticket_data.get("polarity", 0.0)
            urgency_keywords = ticket_data.get("urgency_keywords", [])
            
            needs_escalation = (
                sentiment == "negative" and polarity < -0.3
            ) or len(urgency_keywords) > 0
            
            return {
                "needs_escalation": needs_escalation,
                "escalation_score": abs(polarity) if polarity < 0 else 0.0,
                "reasons": {
                    "negative_sentiment": sentiment == "negative" and polarity < -0.3,
                    "urgency_keywords": len(urgency_keywords) > 0,
                    "urgency_keywords_found": urgency_keywords
                },
                "checked_at": datetime.now().isoformat(),
                "service": "escalation_checker"
            }
        except Exception as e:
            raise Exception(f"Escalation check failed: {str(e)}")
    
    def system_health(self) -> Dict:
        """Get system health status"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "sentiment_analyzer": "active",
                "ticket_processor": "active", 
                "ai_response_generator": "active",
                "escalation_checker": "active"
            },
            "version": "1.0.0",
            "jsonrpc_version": "2.0"
        }
    
    def system_version(self) -> Dict:
        """Get system version information"""
        return {
            "application": "Confluent AI Support Optimizer",
            "version": "1.0.0",
            "jsonrpc_version": "2.0",
            "api_version": "v1",
            "build_date": "2025-06-19",
            "components": {
                "sentiment_analysis": "TextBlob + Custom",
                "ai_responses": "Claude Sonnet 4",
                "streaming": "Confluent Kafka",
                "dashboard": "Gradio"
            }
        }
    
    def handle_request(self, json_request: str) -> str:
        """Handle JSON-RPC 2.0 request"""
        return self.processor.handle_json_string(json_request)