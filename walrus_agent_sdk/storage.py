"""
Storage module for Walrus Agent SDK.

This module provides storage adapters for storing agent conversations and contexts
with three granularity options:
- SUMMARY_ONLY: Store only a summary of the conversation
- FULL_CONVERSATION: Store the complete conversation
- HISTORICAL_VERSIONS: Store full conversation with version history
"""
import os
import json
import time
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class StorageGranularity(Enum):
    """Storage granularity levels for Walrus Agent conversations."""
    SUMMARY_ONLY = "summary_only"
    FULL_CONVERSATION = "full_conversation"
    HISTORICAL_VERSIONS = "historical_versions"

class StorageAdapter:
    """Base storage adapter class."""
    
    def __init__(self, agent_name: str, storage_dir: str = ".walrus_storage"):
        self.agent_name = agent_name
        self.storage_dir = storage_dir
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Ensure the storage directory exists."""
        agent_dir = os.path.join(self.storage_dir, self.agent_name)
        os.makedirs(agent_dir, exist_ok=True)
    
    def _get_agent_dir(self) -> str:
        """Get the agent's storage directory."""
        return os.path.join(self.storage_dir, self.agent_name)
    
    def store(self, data: Any, context_id: Optional[str] = None) -> str:
        """Store data in the storage adapter."""
        raise NotImplementedError("Subclasses must implement store method")
    
    def retrieve(self, context_id: str) -> Any:
        """Retrieve data from the storage adapter."""
        raise NotImplementedError("Subclasses must implement retrieve method")
    
    def list_contexts(self) -> List[str]:
        """List all available contexts."""
        raise NotImplementedError("Subclasses must implement list_contexts method")
    
    def delete(self, context_id: str) -> bool:
        """Delete a context."""
        raise NotImplementedError("Subclasses must implement delete method")

class SummaryOnlyStorage(StorageAdapter):
    """Storage adapter that only stores conversation summaries."""
    
    def store(self, data: Dict[str, Any], context_id: Optional[str] = None) -> str:
        """Store only a summary of the conversation."""
        if context_id is None:
            context_id = f"{int(time.time())}"
            
        # Extract or generate summary
        if "summary" in data:
            summary = data["summary"]
        else:
            # Take last message or a subset of conversation as summary
            messages = data.get("messages", [])
            if messages:
                summary = messages[-1].get("content", "No content available")
            else:
                summary = "Empty conversation"
        
        # Store just the summary
        storage_data = {
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
            "context_id": context_id
        }
        
        file_path = os.path.join(self._get_agent_dir(), f"{context_id}.json")
        with open(file_path, 'w') as f:
            json.dump(storage_data, f, indent=2)
        
        logger.debug(f"Stored summary for context {context_id}")
        return context_id
    
    def retrieve(self, context_id: str) -> Dict[str, Any]:
        """Retrieve the summary for a context."""
        file_path = os.path.join(self._get_agent_dir(), f"{context_id}.json")
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Context {context_id} not found")
            return {"error": f"Context {context_id} not found"}
    
    def list_contexts(self) -> List[Dict[str, str]]:
        """List all available contexts with their summaries."""
        contexts = []
        agent_dir = self._get_agent_dir()
        for filename in os.listdir(agent_dir):
            if filename.endswith('.json'):
                context_id = filename[:-5]  # Remove .json extension
                try:
                    with open(os.path.join(agent_dir, filename), 'r') as f:
                        data = json.load(f)
                        contexts.append({
                            "context_id": context_id,
                            "summary": data.get("summary", "No summary"),
                            "timestamp": data.get("timestamp", "Unknown")
                        })
                except Exception as e:
                    logger.error(f"Error reading context {context_id}: {e}")
        
        return sorted(contexts, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def delete(self, context_id: str) -> bool:
        """Delete a context."""
        file_path = os.path.join(self._get_agent_dir(), f"{context_id}.json")
        try:
            os.remove(file_path)
            logger.debug(f"Deleted context {context_id}")
            return True
        except FileNotFoundError:
            logger.error(f"Context {context_id} not found")
            return False

class FullConversationStorage(StorageAdapter):
    """Storage adapter that stores the full conversation."""
    
    def store(self, data: Dict[str, Any], context_id: Optional[str] = None) -> str:
        """Store the full conversation."""
        if context_id is None:
            context_id = f"{int(time.time())}"
        
        # Ensure we have a timestamp
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()
        
        data["context_id"] = context_id
        
        file_path = os.path.join(self._get_agent_dir(), f"{context_id}.json")
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Stored full conversation for context {context_id}")
        return context_id
    
    def retrieve(self, context_id: str) -> Dict[str, Any]:
        """Retrieve the full conversation for a context."""
        file_path = os.path.join(self._get_agent_dir(), f"{context_id}.json")
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Context {context_id} not found")
            return {"error": f"Context {context_id} not found"}
    
    def list_contexts(self) -> List[Dict[str, str]]:
        """List all available contexts with brief summaries."""
        contexts = []
        agent_dir = self._get_agent_dir()
        for filename in os.listdir(agent_dir):
            if filename.endswith('.json'):
                context_id = filename[:-5]  # Remove .json extension
                try:
                    with open(os.path.join(agent_dir, filename), 'r') as f:
                        data = json.load(f)
                        # Extract a brief summary
                        messages = data.get("messages", [])
                        if messages:
                            summary = messages[-1].get("content", "No content")[:100] + "..."
                        else:
                            summary = "Empty conversation"
                            
                        contexts.append({
                            "context_id": context_id,
                            "summary": summary,
                            "timestamp": data.get("timestamp", "Unknown"),
                            "message_count": len(messages)
                        })
                except Exception as e:
                    logger.error(f"Error reading context {context_id}: {e}")
        
        return sorted(contexts, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def delete(self, context_id: str) -> bool:
        """Delete a context."""
        file_path = os.path.join(self._get_agent_dir(), f"{context_id}.json")
        try:
            os.remove(file_path)
            logger.debug(f"Deleted context {context_id}")
            return True
        except FileNotFoundError:
            logger.error(f"Context {context_id} not found")
            return False

class HistoricalVersionsStorage(StorageAdapter):
    """Storage adapter that stores full conversation with version history."""
    
    def store(self, data: Dict[str, Any], context_id: Optional[str] = None) -> str:
        """Store the full conversation with version history."""
        if context_id is None:
            context_id = f"{int(time.time())}"
        
        # Ensure we have a timestamp
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()
        
        data["context_id"] = context_id
        
        # Create version directory if it doesn't exist
        context_dir = os.path.join(self._get_agent_dir(), context_id)
        os.makedirs(context_dir, exist_ok=True)
        
        # Get current version number
        version = self._get_next_version(context_dir)
        
        # Add version info to data
        data["version"] = version
        
        # Store this version
        file_path = os.path.join(context_dir, f"v{version}.json")
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Also write a latest.json file for easy access
        latest_path = os.path.join(context_dir, "latest.json")
        with open(latest_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Stored version {version} for context {context_id}")
        return context_id
    
    def _get_next_version(self, context_dir: str) -> int:
        """Get the next version number for a context."""
        versions = [0]  # Start at 1 if no versions exist
        for filename in os.listdir(context_dir):
            if filename.startswith('v') and filename.endswith('.json'):
                try:
                    version = int(filename[1:-5])  # Extract number from vX.json
                    versions.append(version)
                except ValueError:
                    pass
        
        return max(versions) + 1
    
    def retrieve(self, context_id: str, version: Optional[int] = None) -> Dict[str, Any]:
        """Retrieve a specific version or latest version of a context."""
        context_dir = os.path.join(self._get_agent_dir(), context_id)
        
        if not os.path.exists(context_dir):
            logger.error(f"Context {context_id} not found")
            return {"error": f"Context {context_id} not found"}
        
        if version is None:
            # Get latest version
            file_path = os.path.join(context_dir, "latest.json")
        else:
            # Get specific version
            file_path = os.path.join(context_dir, f"v{version}.json")
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Version {version} for context {context_id} not found")
            return {"error": f"Version {version} for context {context_id} not found"}
    
    def list_versions(self, context_id: str) -> List[Dict[str, Any]]:
        """List all versions for a context."""
        context_dir = os.path.join(self._get_agent_dir(), context_id)
        
        if not os.path.exists(context_dir):
            logger.error(f"Context {context_id} not found")
            return []
        
        versions = []
        for filename in os.listdir(context_dir):
            if filename.startswith('v') and filename.endswith('.json'):
                try:
                    version = int(filename[1:-5])  # Extract number from vX.json
                    with open(os.path.join(context_dir, filename), 'r') as f:
                        data = json.load(f)
                        versions.append({
                            "version": version,
                            "timestamp": data.get("timestamp", "Unknown"),
                            "message_count": len(data.get("messages", []))
                        })
                except Exception as e:
                    logger.error(f"Error reading version {filename}: {e}")
        
        return sorted(versions, key=lambda x: x["version"])
    
    def list_contexts(self) -> List[Dict[str, str]]:
        """List all available contexts."""
        contexts = []
        agent_dir = self._get_agent_dir()
        
        for dirname in os.listdir(agent_dir):
            context_dir = os.path.join(agent_dir, dirname)
            if os.path.isdir(context_dir):
                latest_path = os.path.join(context_dir, "latest.json")
                if os.path.exists(latest_path):
                    try:
                        with open(latest_path, 'r') as f:
                            data = json.load(f)
                            # Get version count
                            version_count = len([f for f in os.listdir(context_dir) 
                                              if f.startswith('v') and f.endswith('.json')])
                            
                            # Extract a brief summary
                            messages = data.get("messages", [])
                            if messages:
                                summary = messages[-1].get("content", "No content")[:100] + "..."
                            else:
                                summary = "Empty conversation"
                                
                            contexts.append({
                                "context_id": dirname,
                                "summary": summary,
                                "timestamp": data.get("timestamp", "Unknown"),
                                "version_count": version_count,
                                "latest_version": data.get("version", 0)
                            })
                    except Exception as e:
                        logger.error(f"Error reading context {dirname}: {e}")
        
        return sorted(contexts, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def delete(self, context_id: str) -> bool:
        """Delete a context and all its versions."""
        context_dir = os.path.join(self._get_agent_dir(), context_id)
        
        if not os.path.exists(context_dir):
            logger.error(f"Context {context_id} not found")
            return False
        
        try:
            # Delete all files in the context directory
            for filename in os.listdir(context_dir):
                os.remove(os.path.join(context_dir, filename))
            # Remove the directory
            os.rmdir(context_dir)
            logger.debug(f"Deleted context {context_id} and all versions")
            return True
        except Exception as e:
            logger.error(f"Error deleting context {context_id}: {e}")
            return False
    
    def delete_version(self, context_id: str, version: int) -> bool:
        """Delete a specific version of a context."""
        file_path = os.path.join(self._get_agent_dir(), context_id, f"v{version}.json")
        
        if not os.path.exists(file_path):
            logger.error(f"Version {version} for context {context_id} not found")
            return False
        
        try:
            os.remove(file_path)
            logger.debug(f"Deleted version {version} for context {context_id}")
            
            # Update latest.json if needed
            context_dir = os.path.join(self._get_agent_dir(), context_id)
            versions = self.list_versions(context_id)
            
            if versions:
                # Get highest remaining version
                highest_version = max(versions, key=lambda x: x["version"])
                highest_file = os.path.join(context_dir, f"v{highest_version['version']}.json")
                latest_file = os.path.join(context_dir, "latest.json")
                
                # Copy highest version to latest.json
                with open(highest_file, 'r') as src, open(latest_file, 'w') as dst:
                    dst.write(src.read())
            
            return True
        except Exception as e:
            logger.error(f"Error deleting version {version} for context {context_id}: {e}")
            return False

def get_storage_adapter(granularity: StorageGranularity, agent_name: str, 
                       storage_dir: str = ".walrus_storage") -> StorageAdapter:
    """Factory function to get the appropriate storage adapter."""
    if granularity == StorageGranularity.SUMMARY_ONLY:
        return SummaryOnlyStorage(agent_name, storage_dir)
    elif granularity == StorageGranularity.FULL_CONVERSATION:
        return FullConversationStorage(agent_name, storage_dir)
    elif granularity == StorageGranularity.HISTORICAL_VERSIONS:
        return HistoricalVersionsStorage(agent_name, storage_dir)
    else:
        raise ValueError(f"Unknown storage granularity: {granularity}")
