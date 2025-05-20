"""
Configuration module for Walrus Agent SDK.
"""
import os
import logging
from enum import Enum, auto

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# SDK Configuration
DEFAULT_AGENT_NAME = "walrus_agent"
DEFAULT_SUI_RPC_URL = "https://fullnode.devnet.sui.io:443"
DEFAULT_STORAGE_DIRECTORY = ".walrus_storage"

# Environment variable keys
ENV_SUI_RPC_URL = "WALRUS_SUI_RPC_URL"
ENV_SUI_PRIVATE_KEY = "WALRUS_SUI_PRIVATE_KEY"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"

# Get environment variables
SUI_RPC_URL = os.getenv(ENV_SUI_RPC_URL, DEFAULT_SUI_RPC_URL)
SUI_PRIVATE_KEY = os.getenv(ENV_SUI_PRIVATE_KEY, "")
OPENAI_API_KEY = os.getenv(ENV_OPENAI_API_KEY, "")

# Constants
POLLING_INTERVAL = 5  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass

def validate_config():
    """Validate the SDK configuration."""
    if not SUI_PRIVATE_KEY:
        logger.warning("SUI_PRIVATE_KEY not set. Some blockchain operations may fail.")
    
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set. LLM operations will fail.")
