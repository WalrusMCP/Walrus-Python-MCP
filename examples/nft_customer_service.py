"""
NFT Customer Service Bot Example

This example demonstrates how to create an AI agent that serves as a customer service
bot for NFT-related queries. It monitors NFT transfer events and answers user questions
about NFTs.

To run this example:
1. Set up the required environment variables (OPENAI_API_KEY, WALRUS_SUI_RPC_URL, WALRUS_SUI_PRIVATE_KEY)
2. Run this script: python nft_customer_service.py
3. Access the web interface at http://localhost:5000
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from walrus_agent_sdk import WalrusAgent, StorageGranularity
from walrus_agent_sdk.blockchain import EventType, BlockchainClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "walrus_nft_service_secret")

# Initialize agent
agent = WalrusAgent(
    agent_name="__AGENT_NAME__",
    storage_granularity=StorageGranularity.FULL_CONVERSATION,
    system_prompt="""You are an NFT Customer Service AI assistant. You help users with:
1. Information about their NFT collections
2. Explaining recent NFT transfers
3. Providing details about specific NFTs
4. Answering general questions about NFTs on the Sui blockchain

Always be helpful, concise, and accurate. When responding about blockchain data, 
provide clear explanations without technical jargon unless specifically asked for it."""
)

# Initialize blockchain client
blockchain_client = BlockchainClient()

# Global conversation context tracking
conversation_contexts = {}

# NFT Collection data (normally this would come from the blockchain)
NFT_COLLECTIONS = {
    "SuiOrigins": {
        "description": "The first official NFT collection on Sui blockchain",
        "total_items": 10000,
        "floor_price": 0.5,
        "volume_24h": 10.45
    },
    "SuiPunks": {
        "description": "Pixel art avatars for the Sui ecosystem",
        "total_items": 8888,
        "floor_price": 0.3,
        "volume_24h": 5.22
    },
    "MoveLoot": {
        "description": "On-chain generated gear for blockchain adventurers",
        "total_items": 7777,
        "floor_price": 0.8, 
        "volume_24h": 15.1
    }
}

@agent.on_event("nft_transfer")
def handle_nft_transfer(event_data):
    """Handle NFT transfer events."""
    logger.info(f"Processing NFT transfer event: {event_data}")
    
    # Prepare context data
    context_data = {
        "event_type": "NFT Transfer",
        "timestamp": datetime.now().isoformat(),
        "event_data": event_data
    }
    
    # Process with agent
    prompt = """
    An NFT transfer event has occurred. Please analyze the details and provide a summary:
    1. What NFT was transferred?
    2. Who was the sender and recipient?
    3. What was the transaction value (if applicable)?
    4. Any other relevant details about this transfer.
    
    Format your response as a concise notification that could be sent to the users involved.
    """
    
    response = agent.process(prompt, context_data)
    
    logger.info(f"NFT transfer processed: {response['response']}")
    return response

@app.route('/')
def index():
    """Home page - NFT Customer Service interface."""
    # Start a new conversation if none exists
    user_id = session.get('user_id')
    if not user_id:
        user_id = f"user_{int(datetime.now().timestamp())}"
        session['user_id'] = user_id
    
    # Get or create context ID for this user
    if user_id not in conversation_contexts:
        conversation_contexts[user_id] = None
    
    # Get available NFT collections for the sidebar
    collections = list(NFT_COLLECTIONS.keys())
    
    return render_template('nft_customer_service.html', 
                          collections=collections,
                          context_id=conversation_contexts[user_id])

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for the chat interface."""
    data = request.get_json()
    user_message = data.get('message', '')
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Session expired. Please refresh the page."}), 400
    
    # Get context ID for this user
    context_id = conversation_contexts.get(user_id)
    
    # Process the message
    try:
        # Check if user is asking about an NFT collection
        collection_context = {}
        for collection_name in NFT_COLLECTIONS:
            if collection_name.lower() in user_message.lower():
                collection_context = {
                    "nft_collection": collection_name,
                    "collection_data": NFT_COLLECTIONS[collection_name]
                }
                break
        
        # Process with agent
        response = agent.process(user_message, collection_context, context_id)
        
        # Update the conversation context
        conversation_contexts[user_id] = response['context_id']
        
        # Return the response
        return jsonify({
            "response": response['response'],
            "context_id": response['context_id']
        })
    
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        return jsonify({"error": f"Failed to process message: {str(e)}"}), 500

@app.route('/api/nft_collections')
def get_nft_collections():
    """API endpoint to get NFT collections."""
    return jsonify(NFT_COLLECTIONS)

@app.route('/api/clear_conversation', methods=['POST'])
def clear_conversation():
    """Clear the current conversation."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Session expired. Please refresh the page."}), 400
    
    # Clear the context
    conversation_contexts[user_id] = None
    agent.clear_current_context()
    
    return jsonify({"success": True})

@app.route('/api/simulate_nft_transfer', methods=['POST'])
def simulate_nft_transfer():
    """Simulate an NFT transfer event for testing."""
    data = request.get_json()
    collection = data.get('collection', 'SuiOrigins')
    token_id = data.get('token_id', '1234')
    from_address = data.get('from_address', '0xSenderAddress123')
    to_address = data.get('to_address', '0xRecipientAddress456')
    
    # Create a mock event
    mock_event = {
        "type": "nft_transfer",
        "timestamp": datetime.now().timestamp(),
        "data": {
            "collection_name": collection,
            "token_id": token_id,
            "from_address": from_address,
            "to_address": to_address,
            "transaction_hash": f"0x{os.urandom(32).hex()}",
            "value": round(NFT_COLLECTIONS.get(collection, {}).get("floor_price", 0.5) * 1.1, 2)
        }
    }
    
    # Process the event
    response = handle_nft_transfer(mock_event)
    
    return jsonify({
        "success": True,
        "event": mock_event,
        "response": response['response']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
