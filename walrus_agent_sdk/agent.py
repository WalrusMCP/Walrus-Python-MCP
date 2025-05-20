"""
Agent module for Walrus Agent SDK.

This module provides the main WalrusAgent class that connects AI/LLM agents to
Sui blockchain applications with minimal code integration.
"""
import os
import time
import json
import logging
from typing import Dict, List, Any, Callable, Optional, Union, TypeVar, Generic
from enum import Enum
import threading
from functools import wraps

from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.schema import (
    HumanMessage,
    SystemMessage,
    AIMessage
)

from walrus_agent_sdk.storage import (
    StorageGranularity, 
    get_storage_adapter
)
from walrus_agent_sdk.blockchain import (
    BlockchainClient,
    EventType,
    BlockchainError
)
from walrus_agent_sdk.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Type variable for decorator return types
T = TypeVar('T')

class WalrusAgentError(Exception):
    """Exception raised for Walrus Agent errors."""
    pass

class WalrusAgent:
    """
    Main agent class for connecting AI/LLM agents to Sui blockchain.
    
    Key features:
    - Minimal code integration with AI/LLM agents
    - Automatic context storage with different granularity options
    - Sui blockchain event monitoring and action execution
    """
    
    def __init__(
        self,
        agent_name: str,
        storage_granularity: StorageGranularity = StorageGranularity.FULL_CONVERSATION,
        storage_dir: str = ".walrus_storage",
        model_name: str = "gpt-3.5-turbo",
        blockchain_client: Optional[BlockchainClient] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize a Walrus Agent.
        
        Args:
            agent_name: Name of the agent
            storage_granularity: Level of detail for conversation storage
            storage_dir: Directory to store conversation data
            model_name: LLM model to use
            blockchain_client: Client for blockchain interactions
            system_prompt: Base system prompt for the LLM
        """
        self.agent_name = agent_name
        self.storage_granularity = storage_granularity
        self.storage_adapter = get_storage_adapter(storage_granularity, agent_name, storage_dir)
        self.model_name = model_name
        self.blockchain_client = blockchain_client or BlockchainClient()
        
        # Set up default system prompt if none provided
        if system_prompt is None:
            system_prompt = f"""You are {agent_name}, an AI assistant connected to the Sui blockchain.
You can interact with blockchain data and respond to events. Be helpful, concise, and accurate.
When asked about blockchain data, provide clear explanations."""
        
        self.system_prompt = system_prompt
        self.memory = ConversationBufferMemory(return_messages=True)
        
        # Set up LLM (Language Model)
        if not OPENAI_API_KEY:
            logger.warning("OpenAI API key not set. LLM operations will fail.")
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY
        )
        
        # Event handlers
        self.event_handlers = {}
        self.event_subscriptions = {}
        
        # Current context tracking
        self.current_context_id = None
        
        logger.info(f"Initialized Walrus Agent '{agent_name}' with {storage_granularity.value} storage")
    
    def process(
        self, 
        input_text: str, 
        context_data: Optional[Dict[str, Any]] = None,
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an input with the AI agent.
        
        Args:
            input_text: The user input text
            context_data: Additional context data for the conversation
            context_id: Optional context ID for continuing a conversation
            
        Returns:
            Dict containing the agent response and conversation data
        """
        # Retrieve previous context if provided
        if context_id:
            try:
                previous_data = self.storage_adapter.retrieve(context_id)
                # Restore memory from previous conversation
                if "messages" in previous_data:
                    for msg in previous_data["messages"]:
                        if msg["role"] == "user":
                            self.memory.chat_memory.add_user_message(msg["content"])
                        elif msg["role"] == "assistant":
                            self.memory.chat_memory.add_ai_message(msg["content"])
                        elif msg["role"] == "system":
                            self.memory.chat_memory.add_message(SystemMessage(content=msg["content"]))
                
                logger.debug(f"Restored context from ID {context_id}")
                self.current_context_id = context_id
            except Exception as e:
                logger.error(f"Failed to retrieve context {context_id}: {e}")
                # Start a new context if retrieving fails
                self.current_context_id = None
                self.memory = ConversationBufferMemory(return_messages=True)
        
        # Add context data to the prompt if provided
        context_str = ""
        if context_data:
            context_str = "\n\nAdditional context:\n"
            for key, value in context_data.items():
                if isinstance(value, (dict, list)):
                    context_str += f"{key}: {json.dumps(value, indent=2)}\n"
                else:
                    context_str += f"{key}: {value}\n"
        
        full_prompt = f"{input_text}{context_str}"
        
        # Add user message to memory
        self.memory.chat_memory.add_user_message(full_prompt)
        
        # Get messages from memory
        messages = self.memory.chat_memory.messages
        
        # Ensure system message is first
        if not messages or not any(isinstance(msg, SystemMessage) for msg in messages):
            messages.insert(0, SystemMessage(content=self.system_prompt))
        
        # Generate response from LLM
        try:
            response = self.llm.generate([messages])
            ai_message = response.generations[0][0].message
            assistant_response = ai_message.content
            
            # Add assistant response to memory
            self.memory.chat_memory.add_ai_message(assistant_response)
            
            # Convert memory to storable format
            storable_messages = []
            for msg in self.memory.chat_memory.messages:
                if isinstance(msg, SystemMessage):
                    storable_messages.append({"role": "system", "content": msg.content})
                elif isinstance(msg, HumanMessage):
                    storable_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    storable_messages.append({"role": "assistant", "content": msg.content})
            
            # Create storage data
            storage_data = {
                "messages": storable_messages,
                "timestamp": time.time(),
                "model": self.model_name,
                "agent_name": self.agent_name
            }
            
            # Store the conversation
            self.current_context_id = self.storage_adapter.store(
                storage_data, 
                context_id=self.current_context_id
            )
            
            return {
                "response": assistant_response,
                "context_id": self.current_context_id,
                "messages": storable_messages
            }
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            raise WalrusAgentError(f"Failed to process input: {e}")
    
    def on_event(self, event_name: str, filter_params: Optional[Dict[str, Any]] = None):
        """
        Decorator for handling blockchain events.
        
        Args:
            event_name: Name of the event to handle
            filter_params: Optional parameters to filter events
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable[[Dict[str, Any]], T]) -> Callable[[Dict[str, Any]], T]:
            @wraps(func)
            def wrapper(event_data: Dict[str, Any]) -> T:
                # Log event handling
                logger.debug(f"Handling {event_name} event: {event_data}")
                
                # Call the handler function
                return func(event_data)
            
            # Register the event handler
            self._register_event_handler(event_name, wrapper, filter_params)
            return wrapper
        
        return decorator
    
    def _register_event_handler(
        self, 
        event_name: str, 
        handler: Callable[[Dict[str, Any]], Any],
        filter_params: Optional[Dict[str, Any]] = None
    ):
        """
        Register an event handler for blockchain events.
        
        Args:
            event_name: Name of the event to handle
            handler: Function to call when the event occurs
            filter_params: Optional parameters to filter events
        """
        # Determine event type from name
        try:
            event_type = EventType[event_name.upper()]
        except KeyError:
            # If not a predefined event type, use CUSTOM
            event_type = EventType.CUSTOM
            # Add event name to filter parameters
            if filter_params is None:
                filter_params = {}
            filter_params["type"] = event_name
        
        # Store the handler
        self.event_handlers[event_name] = handler
        
        # Subscribe to the event
        subscription_id = self.blockchain_client.subscribe_to_events(
            event_type,
            handler,
            filter_params
        )
        
        # Store the subscription ID
        self.event_subscriptions[event_name] = subscription_id
        
        logger.info(f"Registered handler for {event_name} events with subscription {subscription_id}")
    
    def remove_event_handler(self, event_name: str) -> bool:
        """
        Remove an event handler.
        
        Args:
            event_name: Name of the event handler to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        if event_name in self.event_subscriptions:
            subscription_id = self.event_subscriptions[event_name]
            success = self.blockchain_client.unsubscribe_from_events(subscription_id)
            
            if success:
                del self.event_subscriptions[event_name]
                del self.event_handlers[event_name]
                logger.info(f"Removed handler for {event_name} events")
                return True
        
        logger.warning(f"No handler found for {event_name} events")
        return False
    
    def execute_blockchain_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action on the blockchain.
        
        Args:
            action_data: Data for the blockchain action
            
        Returns:
            Result of the blockchain action
        """
        try:
            result = self.blockchain_client.execute_transaction(action_data)
            logger.info(f"Executed blockchain action: {result}")
            return result
        except BlockchainError as e:
            logger.error(f"Failed to execute blockchain action: {e}")
            raise WalrusAgentError(f"Failed to execute blockchain action: {e}")
    
    def get_blockchain_object(self, object_id: str) -> Dict[str, Any]:
        """
        Get an object from the blockchain.
        
        Args:
            object_id: The object ID to retrieve
            
        Returns:
            Object data
        """
        try:
            result = self.blockchain_client.get_object(object_id)
            return result
        except BlockchainError as e:
            logger.error(f"Failed to get blockchain object {object_id}: {e}")
            raise WalrusAgentError(f"Failed to get blockchain object {object_id}: {e}")
    
    def get_conversation_history(self, context_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Args:
            context_id: Optional context ID (defaults to current context)
            
        Returns:
            List of conversation messages
        """
        context_id = context_id or self.current_context_id
        
        if not context_id:
            return []
        
        try:
            data = self.storage_adapter.retrieve(context_id)
            return data.get("messages", [])
        except Exception as e:
            logger.error(f"Failed to get conversation history for context {context_id}: {e}")
            return []
    
    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        List all conversations for this agent.
        
        Returns:
            List of conversation metadata
        """
        try:
            return self.storage_adapter.list_contexts()
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []
    
    def clear_current_context(self):
        """Clear the current conversation context."""
        self.current_context_id = None
        self.memory = ConversationBufferMemory(return_messages=True)
        logger.debug("Cleared current conversation context")
    
    def delete_conversation(self, context_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            context_id: The context ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            success = self.storage_adapter.delete(context_id)
            
            # If deleting the current context, clear it
            if success and context_id == self.current_context_id:
                self.clear_current_context()
            
            return success
        except Exception as e:
            logger.error(f"Failed to delete conversation {context_id}: {e}")
            return False
