"""
Tests for the storage adapters.
"""
import os
import json
import pytest
import time
from datetime import datetime
from unittest.mock import patch

from walrus_agent_sdk.storage import (
    StorageGranularity,
    StorageAdapter,
    SummaryOnlyStorage,
    FullConversationStorage,
    HistoricalVersionsStorage,
    get_storage_adapter
)

# Test configuration
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
def sample_conversation():
    """Fixture to provide a sample conversation."""
    return {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you for asking. How can I help you today?"},
            {"role": "user", "content": "What's the weather like?"},
            {"role": "assistant", "content": "I don't have access to real-time weather data. You would need to check a weather service or app for that information."}
        ],
        "timestamp": time.time(),
        "model": "gpt-3.5-turbo",
        "agent_name": TEST_AGENT_NAME
    }

@pytest.fixture
def summary_storage(cleanup_storage):
    """Fixture to create a summary-only storage adapter."""
    return SummaryOnlyStorage(TEST_AGENT_NAME, TEST_STORAGE_DIR)

@pytest.fixture
def full_storage(cleanup_storage):
    """Fixture to create a full conversation storage adapter."""
    return FullConversationStorage(TEST_AGENT_NAME, TEST_STORAGE_DIR)

@pytest.fixture
def historical_storage(cleanup_storage):
    """Fixture to create a historical versions storage adapter."""
    return HistoricalVersionsStorage(TEST_AGENT_NAME, TEST_STORAGE_DIR)

def test_get_storage_adapter():
    """Test the storage adapter factory function."""
    summary = get_storage_adapter(StorageGranularity.SUMMARY_ONLY, TEST_AGENT_NAME, TEST_STORAGE_DIR)
    assert isinstance(summary, SummaryOnlyStorage)
    
    full = get_storage_adapter(StorageGranularity.FULL_CONVERSATION, TEST_AGENT_NAME, TEST_STORAGE_DIR)
    assert isinstance(full, FullConversationStorage)
    
    historical = get_storage_adapter(StorageGranularity.HISTORICAL_VERSIONS, TEST_AGENT_NAME, TEST_STORAGE_DIR)
    assert isinstance(historical, HistoricalVersionsStorage)
    
    with pytest.raises(ValueError):
        get_storage_adapter("invalid_granularity", TEST_AGENT_NAME, TEST_STORAGE_DIR)

def test_summary_storage(summary_storage, sample_conversation):
    """Test summary-only storage adapter."""
    # Store the conversation
    context_id = summary_storage.store(sample_conversation)
    assert context_id is not None
    
    # Retrieve the summary
    result = summary_storage.retrieve(context_id)
    assert "summary" in result
    assert result["summary"] == sample_conversation["messages"][-1]["content"]
    
    # List contexts
    contexts = summary_storage.list_contexts()
    assert len(contexts) == 1
    assert contexts[0]["context_id"] == context_id
    assert "summary" in contexts[0]
    
    # Delete context
    assert summary_storage.delete(context_id) is True
    contexts = summary_storage.list_contexts()
    assert len(contexts) == 0

def test_full_conversation_storage(full_storage, sample_conversation):
    """Test full conversation storage adapter."""
    # Store the conversation
    context_id = full_storage.store(sample_conversation)
    assert context_id is not None
    
    # Retrieve the conversation
    result = full_storage.retrieve(context_id)
    assert "messages" in result
    assert len(result["messages"]) == len(sample_conversation["messages"])
    assert result["messages"] == sample_conversation["messages"]
    
    # List contexts
    contexts = full_storage.list_contexts()
    assert len(contexts) == 1
    assert contexts[0]["context_id"] == context_id
    assert "message_count" in contexts[0]
    assert contexts[0]["message_count"] == len(sample_conversation["messages"])
    
    # Delete context
    assert full_storage.delete(context_id) is True
    contexts = full_storage.list_contexts()
    assert len(contexts) == 0

def test_historical_versions_storage(historical_storage, sample_conversation):
    """Test historical versions storage adapter."""
    # Store the first version
    context_id = historical_storage.store(sample_conversation)
    assert context_id is not None
    
    # Retrieve the first version
    result = historical_storage.retrieve(context_id)
    assert "messages" in result
    assert "version" in result
    assert result["version"] == 1
    
    # Update with a second version
    sample_conversation["messages"].append({"role": "user", "content": "New message"})
    historical_storage.store(sample_conversation, context_id)
    
    # List versions
    versions = historical_storage.list_versions(context_id)
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    
    # Retrieve specific version
    v1 = historical_storage.retrieve(context_id, 1)
    assert v1["version"] == 1
    assert len(v1["messages"]) == 5  # Original message count
    
    v2 = historical_storage.retrieve(context_id, 2)
    assert v2["version"] == 2
    assert len(v2["messages"]) == 6  # Original + new message
    
    # Retrieve latest version
    latest = historical_storage.retrieve(context_id)
    assert latest["version"] == 2
    
    # Delete specific version
    assert historical_storage.delete_version(context_id, 1) is True
    versions = historical_storage.list_versions(context_id)
    assert len(versions) == 1
    assert versions[0]["version"] == 2
    
    # Delete context
    assert historical_storage.delete(context_id) is True
    contexts = historical_storage.list_contexts()
    assert len(contexts) == 0

def test_storage_with_explicit_context_id(full_storage, sample_conversation):
    """Test storage with an explicitly provided context ID."""
    custom_id = "custom_context_id"
    context_id = full_storage.store(sample_conversation, context_id=custom_id)
    assert context_id == custom_id
    
    result = full_storage.retrieve(custom_id)
    assert "messages" in result
    assert result["context_id"] == custom_id

def test_nonexistent_context(full_storage):
    """Test retrieving a non-existent context."""
    result = full_storage.retrieve("nonexistent_id")
    assert "error" in result

def test_storage_directory_creation(cleanup_storage):
    """Test that storage directories are created as needed."""
    assert not os.path.exists(os.path.join(TEST_STORAGE_DIR, TEST_AGENT_NAME))
    
    storage = FullConversationStorage(TEST_AGENT_NAME, TEST_STORAGE_DIR)
    
    assert os.path.exists(os.path.join(TEST_STORAGE_DIR, TEST_AGENT_NAME))
