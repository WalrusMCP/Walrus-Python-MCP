"""
Walrus Agent MCP SDK
-------------------

A Python SDK that connects AI/LLM agents to Sui blockchain applications with minimal
code integration, automatic context storage, and event triggering support.

Key Features:
- Minimal code integration with AI/LLM agents
- Automatic context storage with three granularity options
- Sui blockchain event monitoring and action execution
- Cross-chain MCP message support
- CLI scaffolding and code generation

Basic usage:
```python
from walrus_agent_sdk import WalrusAgent, StorageGranularity

# Initialize the agent with minimal code
agent = WalrusAgent(
    agent_name="my_agent",
    storage_granularity=StorageGranularity.FULL_CONVERSATION
)

# Connect to blockchain event and register an action
@agent.on_event("nft_transfer")
def handle_nft_transfer(event_data):
    # Process the event with AI/LLM
    response = agent.process("Describe this NFT transfer", event_data)
    return response
```
"""

# Version
__version__ = '0.1.0'

# Import main classes for easier access
from walrus_agent_sdk.agent import WalrusAgent, WalrusAgentError
from walrus_agent_sdk.storage import StorageGranularity, get_storage_adapter
from walrus_agent_sdk.blockchain import EventType, BlockchainClient, BlockchainError

# For convenient imports
__all__ = [
    'WalrusAgent',
    'WalrusAgentError',
    'StorageGranularity',
    'EventType',
    'BlockchainClient',
    'BlockchainError',
    'get_storage_adapter'
]
