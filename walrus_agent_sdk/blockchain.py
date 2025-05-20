"""
Blockchain module for Walrus Agent SDK.

This module provides blockchain connectivity for interacting with the Sui blockchain,
monitoring events, and executing transactions.
"""
import os
import time
import json
import logging
from enum import Enum
from typing import Dict, List, Any, Callable, Optional, Union
import threading
import requests
from datetime import datetime, timedelta

from walrus_agent_sdk.config import SUI_RPC_URL, SUI_PRIVATE_KEY, POLLING_INTERVAL, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Enum representing different types of blockchain events."""
    NFT_TRANSFER = "nft_transfer"
    TOKEN_TRANSFER = "token_transfer"
    OBJECT_CHANGE = "object_change"
    MOVE_EVENT = "move_event"
    EPOCH_CHANGE = "epoch_change"
    CHECKPOINT = "checkpoint"
    CUSTOM = "custom"

class BlockchainError(Exception):
    """Exception raised for blockchain operation errors."""
    pass

class BlockchainClient:
    """Client for interacting with the Sui blockchain."""
    
    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None):
        """
        Initialize the blockchain client.
        
        Args:
            rpc_url: The Sui RPC URL to connect to (defaults to the environment variable)
            private_key: The private key for transactions (defaults to the environment variable)
        """
        self.rpc_url = rpc_url or SUI_RPC_URL
        self.private_key = private_key or SUI_PRIVATE_KEY
        self._event_listeners = {}
        self._event_polling_thread = None
        self._should_stop_polling = threading.Event()
        self._last_processed_checkpoint = None
    
    def _make_rpc_call(self, method: str, params: List[Any] = None) -> Dict[str, Any]:
        """Make an RPC call to the Sui blockchain."""
        if params is None:
            params = []
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                response = requests.post(self.rpc_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    error_msg = result["error"].get("message", str(result["error"]))
                    raise BlockchainError(f"RPC error: {error_msg}")
                
                return result["result"]
            except (requests.RequestException, json.JSONDecodeError) as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    raise BlockchainError(f"Failed to make RPC call after {MAX_RETRIES} retries: {e}")
                
                logger.warning(f"RPC call failed, retrying in {RETRY_DELAY} seconds: {e}")
                time.sleep(RETRY_DELAY)
    
    def get_latest_checkpoint(self) -> int:
        """Get the latest checkpoint number from the blockchain."""
        try:
            result = self._make_rpc_call("sui_getLatestCheckpointSequenceNumber")
            return int(result)
        except Exception as e:
            logger.error(f"Failed to get latest checkpoint: {e}")
            raise BlockchainError(f"Failed to get latest checkpoint: {e}")
    
    def get_events_by_checkpoint(self, checkpoint: int) -> List[Dict[str, Any]]:
        """Get events for a specific checkpoint."""
        try:
            result = self._make_rpc_call("sui_getCheckpointEvents", [checkpoint])
            return result
        except Exception as e:
            logger.error(f"Failed to get events for checkpoint {checkpoint}: {e}")
            return []
    
    def get_transaction_block(self, digest: str) -> Dict[str, Any]:
        """Get a transaction block by digest."""
        try:
            result = self._make_rpc_call("sui_getTransactionBlock", [
                digest,
                {
                    "showEffects": True,
                    "showEvents": True,
                    "showObjectChanges": True
                }
            ])
            return result
        except Exception as e:
            logger.error(f"Failed to get transaction block {digest}: {e}")
            raise BlockchainError(f"Failed to get transaction block {digest}: {e}")
    
    def subscribe_to_events(self, event_type: EventType, callback: Callable[[Dict[str, Any]], None], 
                           filter_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Subscribe to blockchain events.
        
        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when an event is detected
            filter_params: Optional parameters to filter events
            
        Returns:
            Subscription ID
        """
        subscription_id = f"{event_type.value}_{int(time.time())}_{len(self._event_listeners)}"
        
        self._event_listeners[subscription_id] = {
            "event_type": event_type,
            "callback": callback,
            "filter_params": filter_params or {}
        }
        
        # Start the polling thread if it's not already running
        if self._event_polling_thread is None or not self._event_polling_thread.is_alive():
            self._should_stop_polling.clear()
            self._event_polling_thread = threading.Thread(
                target=self._poll_events,
                daemon=True
            )
            self._event_polling_thread.start()
        
        logger.info(f"Subscribed to {event_type.value} events with ID {subscription_id}")
        return subscription_id
    
    def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """
        Unsubscribe from blockchain events.
        
        Args:
            subscription_id: The subscription ID to unsubscribe
            
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        if subscription_id in self._event_listeners:
            del self._event_listeners[subscription_id]
            logger.info(f"Unsubscribed from events with ID {subscription_id}")
            
            # Stop polling if there are no more listeners
            if not self._event_listeners:
                self._should_stop_polling.set()
                if self._event_polling_thread and self._event_polling_thread.is_alive():
                    self._event_polling_thread.join(timeout=5)
                self._event_polling_thread = None
            
            return True
        
        logger.warning(f"Subscription ID {subscription_id} not found")
        return False
    
    def _poll_events(self):
        """Poll for blockchain events in a background thread."""
        logger.info("Starting event polling thread")
        
        if self._last_processed_checkpoint is None:
            # Start from the latest checkpoint
            try:
                self._last_processed_checkpoint = self.get_latest_checkpoint()
                logger.info(f"Starting event polling from checkpoint {self._last_processed_checkpoint}")
            except Exception as e:
                logger.error(f"Failed to get latest checkpoint: {e}")
                self._last_processed_checkpoint = 0
        
        while not self._should_stop_polling.is_set():
            try:
                # Get the latest checkpoint
                latest_checkpoint = self.get_latest_checkpoint()
                
                # Process any new checkpoints
                for checkpoint in range(self._last_processed_checkpoint + 1, latest_checkpoint + 1):
                    events = self.get_events_by_checkpoint(checkpoint)
                    self._process_events(events)
                    self._last_processed_checkpoint = checkpoint
                
                # Wait before polling again
                self._should_stop_polling.wait(POLLING_INTERVAL)
            except Exception as e:
                logger.error(f"Error in event polling: {e}")
                # Wait before retrying
                self._should_stop_polling.wait(RETRY_DELAY)
    
    def _process_events(self, events: List[Dict[str, Any]]):
        """Process blockchain events and call registered callbacks."""
        for event in events:
            # Extract event type
            event_type_str = event.get("type", "")
            
            # Match event to listeners
            for subscription_id, listener in self._event_listeners.items():
                event_type = listener["event_type"]
                filter_params = listener["filter_params"]
                callback = listener["callback"]
                
                # Check if event matches the subscription
                if self._event_matches(event, event_type, filter_params):
                    try:
                        # Call the callback in a try-except to prevent one callback
                        # from breaking the entire event processing loop
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in event callback for subscription {subscription_id}: {e}")
    
    def _event_matches(self, event: Dict[str, Any], event_type: EventType, 
                      filter_params: Dict[str, Any]) -> bool:
        """
        Check if an event matches a subscription.
        
        Args:
            event: The event data
            event_type: The event type to match
            filter_params: Parameters to filter the event
            
        Returns:
            True if the event matches, False otherwise
        """
        # Match by event type
        event_type_str = event.get("type", "")
        
        if event_type == EventType.CUSTOM:
            # For custom events, rely entirely on filter_params
            pass
        elif event_type == EventType.NFT_TRANSFER:
            if "nft" not in event_type_str.lower() and "transfer" not in event_type_str.lower():
                return False
        elif event_type == EventType.TOKEN_TRANSFER:
            if "coin" not in event_type_str.lower() and "transfer" not in event_type_str.lower():
                return False
        elif event_type == EventType.OBJECT_CHANGE:
            if "object" not in event_type_str.lower():
                return False
        elif event_type == EventType.MOVE_EVENT:
            # All events from Move modules should pass this filter
            pass
        elif event_type == EventType.EPOCH_CHANGE:
            if "epoch" not in event_type_str.lower():
                return False
        elif event_type == EventType.CHECKPOINT:
            if "checkpoint" not in event_type_str.lower():
                return False
        
        # Apply additional filters from filter_params
        # Each key in filter_params should match a key in the event with the same value
        for key, value in filter_params.items():
            # Special handling for nested keys with dot notation (e.g., "data.fieldName")
            if "." in key:
                parts = key.split(".")
                current = event
                for part in parts:
                    if not isinstance(current, dict) or part not in current:
                        return False
                    current = current[part]
                
                if current != value:
                    return False
            # Direct key matching
            elif key not in event or event[key] != value:
                return False
        
        return True
    
    def execute_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a transaction on the blockchain.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Transaction result
        """
        if not self.private_key:
            raise BlockchainError("Private key not set. Cannot execute transactions.")
        
        # This is a placeholder for the actual transaction execution logic
        # In a real implementation, this would use the Sui SDK to sign and send the transaction
        # For now, we'll just simulate the process with a mock response
        
        logger.info("Executing transaction (placeholder implementation)")
        
        try:
            # In a real implementation, we would:
            # 1. Create a transaction block
            # 2. Add transaction commands
            # 3. Sign the transaction
            # 4. Execute the transaction
            # 5. Return the result
            
            # For now, return a mock result
            digest = f"mock_tx_{int(time.time())}"
            return {
                "digest": digest,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "effects": {
                    "status": "success",
                    "gasUsed": {"computationCost": "1000", "storageCost": "500", "storageRebate": "200"}
                }
            }
        except Exception as e:
            logger.error(f"Failed to execute transaction: {e}")
            raise BlockchainError(f"Failed to execute transaction: {e}")
    
    def get_object(self, object_id: str) -> Dict[str, Any]:
        """
        Get an object from the blockchain.
        
        Args:
            object_id: The object ID to retrieve
            
        Returns:
            Object data
        """
        try:
            result = self._make_rpc_call("sui_getObject", [
                object_id,
                {
                    "showContent": True,
                    "showDisplay": True,
                    "showOwner": True
                }
            ])
            return result
        except Exception as e:
            logger.error(f"Failed to get object {object_id}: {e}")
            raise BlockchainError(f"Failed to get object {object_id}: {e}")
    
    def get_owned_objects(self, address: str, object_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get objects owned by an address.
        
        Args:
            address: The owner's address
            object_type: Optional type filter for objects
            
        Returns:
            List of owned objects
        """
        filter_params = {}
        if object_type:
            filter_params["StructType"] = object_type
        
        try:
            result = self._make_rpc_call("sui_getOwnedObjects", [
                address,
                filter_params,
                None,  # No cursor for initial request
                100    # Limit to 100 objects
            ])
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get objects owned by {address}: {e}")
            raise BlockchainError(f"Failed to get objects owned by {address}: {e}")
