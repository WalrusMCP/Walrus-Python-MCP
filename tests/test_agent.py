"""
Tests for the WalrusAgent module.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock

from walrus_agent_sdk import WalrusAgent, StorageGranularity
from walrus_agent_sdk.blockchain import BlockchainClient, EventType
from walrus_agent_sdk.agent import WalrusAgentError

# Test agent configuration
TEST_AGENT_NAME = "test_agent"
TEST_STORAGE_DIR = ".test_walrus_storage"

@pytest.fixture(scope="function")
def cleanup_storage():
    """Fixture to clean up test storage before and after tests."""
    import shutil
    
    # Clean up before test
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)
    
    yield
    
    # Clean up after test
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR)

@pytest.fixture
def mock_llm():
    """Fixture to create a mock LLM."""
    with patch('langchain.chat_models.ChatOpenAI') as mock_llm:
        mock_llm_instance = MagicMock()
        mock_generation = MagicMock()
        mock_generation.generations = [[MagicMock(message=MagicMock(content="Mock AI response"))]]
        mock_llm_instance.generate.return_value = mock_generation
        mock_llm.return_value = mock_llm_instance
        yield mock_llm

@pytest.fixture
def mock_blockchain_client():
    """Fixture to create a mock blockchain client."""
    with patch('walrus_agent_sdk.blockchain.BlockchainClient') as mock_client:
        mock_instance = MagicMock()
        mock_instance.subscribe_to_events.return_value = "mock_subscription_id"
        mock_instance.unsubscribe_from_events.return_value = True
        mock_instance.execute_transaction.return_value = {"status": "success", "digest": "mock_digest"}
        mock_instance.get_object.return_value = {"data": {"mock": "object"}}
        yield mock_instance

@pytest.fixture
def test_agent(mock_llm, mock_blockchain_client, cleanup_storage):
    """Fixture to create a test agent."""
    agent = WalrusAgent(
        agent_name=TEST_AGENT_NAME,
        storage_granularity=StorageGranularity.FULL_CONVERSATION,
        storage_dir=TEST_STORAGE_DIR,
        blockchain_client=mock_blockchain_client
    )
    yield agent

def test_agent_initialization(test_agent, mock_blockchain_client):
    """Test agent initialization."""
    assert test_agent.agent_name == TEST_AGENT_NAME
    assert test_agent.storage_granularity == StorageGranularity.FULL_CONVERSATION
    assert test_agent.blockchain_client == mock_blockchain_client

def test_agent_process(test_agent, mock_llm):
    """Test agent processing a message."""
    response = test_agent.process("Hello, agent!")
    
    assert "response" in response
    assert response["response"] == "Mock AI response"
    assert "context_id" in response
    assert response["context_id"] is not None
    
    # Verify storage worked
    contexts = test_agent.list_conversations()
    assert len(contexts) == 1

def test_agent_process_with_context(test_agent, mock_llm):
    """Test agent processing a message with an existing context."""
    # First message to create a context
    first_response = test_agent.process("Hello, agent!")
    context_id = first_response["context_id"]
    
    # Second message using the context
    second_response = test_agent.process("Follow-up question", context_id=context_id)
    
    assert second_response["context_id"] == context_id
    
    # Verify context contains both messages
    history = test_agent.get_conversation_history(context_id)
    assert len(history) == 5  # system prompt + 2 user messages + 2 assistant responses

def test_agent_process_with_context_data(test_agent, mock_llm):
    """Test agent processing a message with additional context data."""
    context_data = {"key": "value", "nested": {"data": "test"}}
    response = test_agent.process("Process with context data", context_data=context_data)
    
    assert "response" in response
    assert response["response"] == "Mock AI response"

def test_agent_event_handler(test_agent, mock_blockchain_client):
    """Test agent event handler registration."""
    # Define a test handler
    @test_agent.on_event("test_event")
    def handle_test_event(event_data):
        return {"processed": True, "event": event_data}
    
    # Verify the handler was registered
    assert "test_event" in test_agent.event_handlers
    assert "test_event" in test_agent.event_subscriptions
    
    # Verify subscription was created
    mock_blockchain_client.subscribe_to_events.assert_called_once()
    
    # Test calling the handler
    test_event = {"type": "test_event", "data": {"test": "data"}}
    result = handle_test_event(test_event)
    
    assert result["processed"] is True
    assert result["event"] == test_event

def test_agent_remove_event_handler(test_agent, mock_blockchain_client):
    """Test removing an event handler."""
    # Register a handler
    @test_agent.on_event("test_event")
    def handle_test_event(event_data):
        return {"processed": True}
    
    # Remove the handler
    result = test_agent.remove_event_handler("test_event")
    
    assert result is True
    assert "test_event" not in test_agent.event_handlers
    assert "test_event" not in test_agent.event_subscriptions
    mock_blockchain_client.unsubscribe_from_events.assert_called_once()

def test_agent_clear_context(test_agent, mock_llm):
    """Test clearing the agent's current context."""
    # Create a context
    response = test_agent.process("Hello, agent!")
    assert test_agent.current_context_id is not None
    
    # Clear the context
    test_agent.clear_current_context()
    assert test_agent.current_context_id is None
    
    # Process a new message
    new_response = test_agent.process("New conversation")
    assert new_response["context_id"] != response["context_id"]

def test_agent_list_conversations(test_agent, mock_llm):
    """Test listing agent conversations."""
    # Create some conversations
    test_agent.process("Conversation 1")
    test_agent.process("Conversation 2")
    test_agent.clear_current_context()
    test_agent.process("Conversation 3")
    
    # List the conversations
    conversations = test_agent.list_conversations()
    
    assert len(conversations) == 3
    assert all("context_id" in conv for conv in conversations)

def test_agent_delete_conversation(test_agent, mock_llm):
    """Test deleting a conversation."""
    # Create a conversation
    response = test_agent.process("Hello, agent!")
    context_id = response["context_id"]
    
    # Delete the conversation
    result = test_agent.delete_conversation(context_id)
    
    assert result is True
    assert test_agent.current_context_id is None
    
    # Verify it's gone
    conversations = test_agent.list_conversations()
    assert len(conversations) == 0

def test_agent_blockchain_actions(test_agent, mock_blockchain_client):
    """Test agent blockchain actions."""
    # Test executing a transaction
    tx_data = {"type": "mock_tx", "data": {"test": "data"}}
    result = test_agent.execute_blockchain_action(tx_data)
    
    assert result["status"] == "success"
    mock_blockchain_client.execute_transaction.assert_called_once_with(tx_data)
    
    # Test getting a blockchain object
    object_result = test_agent.get_blockchain_object("mock_object_id")
    assert "data" in object_result
    mock_blockchain_client.get_object.assert_called_once_with("mock_object_id")
