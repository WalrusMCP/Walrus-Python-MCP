#!/usr/bin/env python3
"""
Walrus Agent MCP SDK - Main Demo

This script demonstrates the basic usage of the Walrus Agent SDK
to connect AI/LLM agents to Sui blockchain applications with minimal
code integration.

To run this demo:
1. Set the required environment variables (OPENAI_API_KEY, WALRUS_SUI_RPC_URL, WALRUS_SUI_PRIVATE_KEY)
2. Run this script: python main.py
"""

import os
import sys
import time
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for

from walrus_agent_sdk.cli import cli

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check for required environment variables
has_openai_key = bool(os.environ.get('OPENAI_API_KEY'))
if not has_openai_key:
    logger.warning("OPENAI_API_KEY environment variable not set. LLM operations will fail.")

if not os.environ.get('WALRUS_SUI_RPC_URL'):
    logger.info("WALRUS_SUI_RPC_URL not set, using default devnet URL.")

if not os.environ.get('WALRUS_SUI_PRIVATE_KEY'):
    logger.warning("WALRUS_SUI_PRIVATE_KEY not set. Blockchain transactions will fail.")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "walrus_agent_demo_secret")

# Only initialize the agent if we have an API key
agent = None
if has_openai_key:
    from walrus_agent_sdk import WalrusAgent, StorageGranularity
    from walrus_agent_sdk.blockchain import EventType, BlockchainClient
    
    # Initialize the Walrus Agent
    agent = WalrusAgent(
        agent_name="walrus_demo_agent",
        storage_granularity=StorageGranularity.FULL_CONVERSATION,
        system_prompt="""You are Walrus Agent, an AI assistant that connects to the Sui blockchain.
    You can help users understand blockchain concepts, interact with the Sui blockchain,
    and demonstrate the capabilities of the Walrus Agent SDK.

    Be concise, helpful, and informative in your responses."""
    )

# Define a function to handle demo events
def handle_demo_event(event_data):
    """Handle demo events."""
    logger.info(f"Processing demo event: {event_data}")
    
    if agent:
        # Process with AI agent
        prompt = """
        I received a blockchain event. Please analyze it and provide insights:
        
        1. What type of event is this?
        2. What does the data represent?
        3. What actions might be appropriate in response?
        """
        
        response = agent.process(prompt, event_data)
        
        logger.info(f"Demo event processed: {response['response']}")
        return response
    else:
        # Return a placeholder response if no agent
        return {
            "response": "API key not configured. Please set the OPENAI_API_KEY environment variable.",
            "context_id": None
        }

@app.route('/')
def index():
    """Home page - Main demo interface."""
    api_key_alert = ""
    if not has_openai_key:
        api_key_alert = """
        <div class="alert alert-warning" role="alert">
            <h4 class="alert-heading">API Key Required</h4>
            <p>OpenAI API Key is not configured. Some features will not work properly.</p>
            <hr>
            <p class="mb-0">Set the <code>OPENAI_API_KEY</code> environment variable to enable full functionality.</p>
        </div>
        """
        
    return f"""
    <html lang="en" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Walrus Agent SDK</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/css/all.min.css">
    </head>
    <body>
        <div class="container py-5">
            <div class="row">
                <div class="col-12 text-center mb-5">
                    <h1 class="display-4">Walrus Agent MCP SDK</h1>
                    <p class="lead">Connect AI/LLM agents to Sui blockchain applications with minimal code integration</p>
                </div>
            </div>
            
            {api_key_alert}
            
            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-robot me-2"></i>NFT Customer Service Bot</h5>
                            <p class="card-text">An AI assistant that serves as a customer service bot for NFT-related queries and monitors NFT transfer events.</p>
                            <a href="/examples/nft_customer_service" class="btn btn-primary">Try Demo</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-chart-line me-2"></i>RWA Data Oracle</h5>
                            <p class="card-text">An AI agent that serves as a data oracle for real-world assets, analyzing blockchain events and external data.</p>
                            <a href="/examples/rwa_data_oracle" class="btn btn-primary">Try Demo</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-coins me-2"></i>Auto Market Maker</h5>
                            <p class="card-text">An automated market making bot that monitors conditions and adjusts positions based on AI recommendations.</p>
                            <a href="/examples/auto_market_maker" class="btn btn-primary">Try Demo</a>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-terminal me-2"></i>CLI Tools</h5>
                            <p class="card-text">Scaffolding and code generation tools to quickly set up blockchain-connected AI agents.</p>
                            <div class="bg-dark p-3 rounded">
                                <code>python -m walrus_agent_sdk.cli create --agent-name my_agent --template nft_customer_service</code>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">Minimal Integration Code</h5>
                        </div>
                        <div class="card-body">
                            <pre class="bg-dark p-3 rounded text-light"><code>from walrus_agent_sdk import WalrusAgent, StorageGranularity

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
    return response</code></pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <footer class="bg-dark text-light py-4 mt-5">
            <div class="container text-center">
                <p>Walrus Agent MCP SDK - Connect AI/LLM agents to the Sui blockchain</p>
                <div>
                    <a href="https://github.com/your-org/walrus-agent-sdk" class="text-light me-3">
                        <i class="fab fa-github"></i> GitHub
                    </a>
                    <a href="/docs" class="text-light me-3">
                        <i class="fas fa-book"></i> Documentation
                    </a>
                    <a href="/examples" class="text-light">
                        <i class="fas fa-flask"></i> Examples
                    </a>
                </div>
            </div>
        </footer>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for chat interactions with the agent."""
    if not agent:
        return jsonify({
            "error": "OpenAI API Key not configured. Set the OPENAI_API_KEY environment variable.",
            "success": False
        }), 503
    
    data = request.get_json()
    user_message = data.get('message', '')
    context_id = data.get('context_id')
    
    try:
        # Process the message
        response = agent.process(user_message, context_id=context_id)
        
        return jsonify({
            "response": response['response'],
            "context_id": response['context_id'],
            "success": True
        })
    
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        return jsonify({
            "error": f"Failed to process message: {str(e)}",
            "success": False
        }), 500

@app.route('/api/simulate_event', methods=['POST'])
def simulate_event():
    """API endpoint to simulate a blockchain event."""
    data = request.get_json()
    event_type = data.get('event_type', 'demo_event')
    event_data = data.get('event_data', {})
    
    # Create a mock event
    mock_event = {
        "type": event_type,
        "timestamp": time.time(),
        "data": event_data
    }
    
    # Process the event
    response = handle_demo_event(mock_event)
    
    return jsonify({
        "success": True,
        "event": mock_event,
        "response": response
    })

@app.route('/api/status')
def api_status():
    """API endpoint to check the status of the API."""
    return jsonify({
        "api_key_configured": has_openai_key,
        "agent_initialized": agent is not None,
        "version": "0.1.0"
    })

def run_server():
    """Run the Flask server."""
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    # If arguments are passed, treat as CLI command
    if len(sys.argv) > 1:
        sys.argv.pop(0)  # Remove script name
        cli()
    else:
        # Otherwise run the demo server
        run_server()
