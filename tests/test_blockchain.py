"""
Tests for the blockchain client module.
"""
import os
import json
import pytest
import time
from unittest.mock import patch, MagicMock, call

from walrus_agent_sdk.blockchain import (
    BlockchainClient,
    EventType,
    BlockchainError
)

@pytest.fixture
def mock_requests():
    """Fixture to mock requests."""
    with patch('walrus_agent_sdk.blockchain.requests') as mock_req:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {}}
        mock_req.post.return_value = mock_response
        yield mock_req

@pytest.fixture
def blockchain_client(mock_requests):
    """Fixture to create a blockchain client."""
    return BlockchainClient(
        rpc_url="https://test-rpc.sui.io",
        private_key="test_private_key"
    )

def test_blockchain_client_initialization(blockchain_client):
    """Test blockchain client initialization."""
    assert blockchain_client.rpc_url == "https://test-rpc.sui.io"
    assert blockchain_client.private_key == "test_private_key"
    assert blockchain_client._event_listeners == {}
    assert blockchain_client._event_polling_thread is None

def test_make_rpc_call(blockchain_client, mock_requests):
    """Test making RPC calls."""
    # Set up mock response
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"data": "test_data"}}
    mock_requests.post.return_value = mock_response
    
    # Test the RPC call
    result = blockchain_client._make_rpc_call("test_method", ["param1", "param2"])
    
    # Verify the request
    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert args[0] == "https://test-rpc.sui.io"
    assert kwargs["json"]["method"] == "test_method"
    assert kwargs["json"]["params"] == ["param1", "param2"]
    
    # Verify the result
    assert result == {"data": "test_data"}

def test_make_rpc_call_error(blockchain_client, mock_requests):
    """Test handling RPC call errors."""
    # Set up mock response with error
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "jsonrpc": "2.0", 
        "id": 1, 
        "error": {"code": -32000, "message": "Test error"}
    }
    mock_requests.post.return_value = mock_response
    
    # Test the RPC call
    with pytest.raises(BlockchainError) as exc_info:
        blockchain_client._make_rpc_call("test_method")
    
    assert "Test error" in str(exc_info.value)

def test_make_rpc_call_retry(blockchain_client, mock_requests):
    """Test RPC call retries on failure."""
    # First call fails, second succeeds
    mock_failed_response = MagicMock()
    mock_failed_response.raise_for_status.side_effect = Exception("Connection error")
    
    mock_success_response = MagicMock()
    mock_success_response.raise_for_status.return_value = None
    mock_success_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"data": "test_data"}}
    
    mock_requests.post.side_effect = [mock_failed_response, mock_success_response]
    
    # Test the RPC call
    with patch('walrus_agent_sdk.blockchain.RETRY_DELAY', 0.01):  # Speed up test
        result = blockchain_client._make_rpc_call("test_method")
    
    # Verify retries
    assert mock_requests.post.call_count == 2
    assert result == {"data": "test_data"}

def test_get_latest_checkpoint(blockchain_client, mock_requests):
    """Test getting the latest checkpoint."""
    # Set up mock response
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": 12345}
    mock_requests.post.return_value = mock_response
    
    # Test the method
    result = blockchain_client.get_latest_checkpoint()
    
    # Verify the request
    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert kwargs["json"]["method"] == "sui_getLatestCheckpointSequenceNumber"
    
    # Verify the result
    assert result == 12345

def test_get_events_by_checkpoint(blockchain_client, mock_requests):
    """Test getting events by checkpoint."""
    # Set up mock response
    mock_events = [{"type": "test_event", "data": "test_data"}]
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": mock_events}
    mock_requests.post.return_value = mock_response
    
    # Test the method
    result = blockchain_client.get_events_by_checkpoint(12345)
    
    # Verify the request
    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert kwargs["json"]["method"] == "sui_getCheckpointEvents"
    assert kwargs["json"]["params"] == [12345]
    
    # Verify the result
    assert result == mock_events

def test_get_transaction_block(blockchain_client, mock_requests):
    """Test getting a transaction block."""
    # Set up mock response
    mock_tx_block = {
        "digest": "test_digest",
        "effects": {"status": "success"},
        "events": [{"type": "test_event"}]
    }
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": mock_tx_block}
    mock_requests.post.return_value = mock_response
    
    # Test the method
    result = blockchain_client.get_transaction_block("test_digest")
    
    # Verify the request
    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert kwargs["json"]["method"] == "sui_getTransactionBlock"
    assert kwargs["json"]["params"][0] == "test_digest"
    assert "showEffects" in kwargs["json"]["params"][1]
    
    # Verify the result
    assert result == mock_tx_block

def test_event_subscription(blockchain_client):
    """Test subscribing to events."""
    # Mock event callback
    callback = MagicMock()
    
    # Subscribe to events
    subscription_id = blockchain_client.subscribe_to_events(
        EventType.NFT_TRANSFER,
        callback,
        {"address": "test_address"}
    )
    
    # Verify subscription was registered
    assert subscription_id in blockchain_client._event_listeners
    assert blockchain_client._event_listeners[subscription_id]["event_type"] == EventType.NFT_TRANSFER
    assert blockchain_client._event_listeners[subscription_id]["callback"] == callback
    assert blockchain_client._event_listeners[subscription_id]["filter_params"] == {"address": "test_address"}

def test_event_unsubscription(blockchain_client):
    """Test unsubscribing from events."""
    # Subscribe and then unsubscribe
    callback = MagicMock()
    subscription_id = blockchain_client.subscribe_to_events(EventType.NFT_TRANSFER, callback)
    
    # Verify subscription was registered
    assert subscription_id in blockchain_client._event_listeners
    
    # Unsubscribe
    result = blockchain_client.unsubscribe_from_events(subscription_id)
    
    # Verify unsubscription
    assert result is True
    assert subscription_id not in blockchain_client._event_listeners

def test_event_matching(blockchain_client):
    """Test event matching logic."""
    # Test NFT transfer event matching
    nft_event = {"type": "nft_transfer", "data": {"object_id": "test_id"}}
    assert blockchain_client._event_matches(nft_event, EventType.NFT_TRANSFER, {}) is True
    assert blockchain_client._event_matches(nft_event, EventType.TOKEN_TRANSFER, {}) is False
    
    # Test with filter params
    filtered_event = {"type": "test_event", "address": "test_address", "data": {"value": 100}}
    assert blockchain_client._event_matches(filtered_event, EventType.CUSTOM, {"address": "test_address"}) is True
    assert blockchain_client._event_matches(filtered_event, EventType.CUSTOM, {"address": "wrong_address"}) is False
    
    # Test nested filter params
    nested_event = {"type": "test_event", "data": {"nested": {"value": 100}}}
    assert blockchain_client._event_matches(nested_event, EventType.CUSTOM, {"data.nested.value": 100}) is True
    assert blockchain_client._event_matches(nested_event, EventType.CUSTOM, {"data.nested.value": 200}) is False

@patch('threading.Thread')
def test_event_polling_thread(mock_thread, blockchain_client):
    """Test event polling thread."""
    # Mock the polling method
    with patch.object(blockchain_client, '_poll_events') as mock_poll:
        # Subscribe to events to trigger thread
        callback = MagicMock()
        subscription_id = blockchain_client.subscribe_to_events(EventType.NFT_TRANSFER, callback)
        
        # Verify thread was started
        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]['target'] == blockchain_client._poll_events
        assert mock_thread.call_args[1]['daemon'] is True
        
        # Verify thread was started
        assert mock_thread.return_value.start.called

def test_execute_transaction(blockchain_client):
    """Test executing a transaction."""
    # Prepare test data
    tx_data = {"type": "test_tx", "data": {"value": 100}}
    
    # Execute transaction
    result = blockchain_client.execute_transaction(tx_data)
    
    # Verify result
    assert "digest" in result
    assert "status" in result
    assert result["status"] == "success"

def test_get_object(blockchain_client, mock_requests):
    """Test getting an object."""
    # Set up mock response
    mock_object = {"data": {"type": "test_object", "id": "test_id"}}
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": mock_object}
    mock_requests.post.return_value = mock_response
    
    # Test the method
    result = blockchain_client.get_object("test_id")
    
    # Verify the request
    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert kwargs["json"]["method"] == "sui_getObject"
    assert kwargs["json"]["params"][0] == "test_id"
    
    # Verify the result
    assert result == mock_object

def test_get_owned_objects(blockchain_client, mock_requests):
    """Test getting owned objects."""
    # Set up mock response
    mock_objects = {"data": [{"id": "obj1"}, {"id": "obj2"}]}
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": mock_objects}
    mock_requests.post.return_value = mock_response
    
    # Test the method
    result = blockchain_client.get_owned_objects("test_address", "test_type")
    
    # Verify the request
    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert kwargs["json"]["method"] == "sui_getOwnedObjects"
    assert kwargs["json"]["params"][0] == "test_address"
    assert kwargs["json"]["params"][1]["StructType"] == "test_type"
    
    # Verify the result
    assert result == mock_objects.get("data", [])
