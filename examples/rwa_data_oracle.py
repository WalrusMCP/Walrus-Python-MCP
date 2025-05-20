"""
Real-World Asset (RWA) Data Oracle Example

This example demonstrates how to create an AI agent that serves as a data oracle
for real-world assets. It analyzes blockchain events and external data to provide
insights and updates about real-world assets.

To run this example:
1. Set up the required environment variables (OPENAI_API_KEY, WALRUS_SUI_RPC_URL, WALRUS_SUI_PRIVATE_KEY)
2. Run this script: python rwa_data_oracle.py
"""
import os
import json
import logging
import threading
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

from walrus_agent_sdk import WalrusAgent, StorageGranularity
from walrus_agent_sdk.blockchain import EventType, BlockchainClient
from walrus_agent_sdk.utils import format_timestamp

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "walrus_rwa_oracle_secret")

# Initialize agent
agent = WalrusAgent(
    agent_name="__AGENT_NAME__",
    storage_granularity=StorageGranularity.HISTORICAL_VERSIONS,
    system_prompt="""You are a Real-World Asset (RWA) Data Oracle AI assistant. Your role is to:
1. Analyze real-world asset data and provide insights
2. Monitor changes in asset values and conditions
3. Generate human-readable summaries of asset data
4. Help users understand real-world asset data on the blockchain

Always be objective, data-driven, and precise in your responses. Include relevant
metrics and explain their significance in the context of real-world assets."""
)

# Sample real-world assets (in a real application, this would be on-chain data)
RWA_ASSETS = {
    "tokenized_real_estate": {
        "asset_id": "RE-123456",
        "address": "123 Blockchain Blvd, San Francisco, CA",
        "type": "Commercial Office Building",
        "valuation": 12500000,
        "tokenized_value": 10000000,
        "tokens_issued": 10000,
        "token_price": 1000,
        "occupancy_rate": 95,
        "annual_yield": 7.2,
        "last_appraisal_date": "2023-11-15",
        "risk_rating": "B+"
    },
    "carbon_credits": {
        "asset_id": "CC-789012",
        "project_name": "Amazon Reforestation Initiative",
        "location": "Brazil",
        "credit_type": "Carbon Sequestration",
        "credits_issued": 50000,
        "tokens_issued": 50000,
        "token_price": 15,
        "total_co2_offset": 50000,
        "vintage_year": 2023,
        "verification_body": "Gold Standard",
        "risk_rating": "A-"
    },
    "commodity_receivables": {
        "asset_id": "CR-345678",
        "commodity": "Coffee Beans",
        "origin": "Colombia",
        "quantity": 250000,
        "unit": "kg",
        "grade": "Premium Arabica",
        "valuation": 1750000,
        "tokens_issued": 17500,
        "token_price": 100,
        "harvest_date": "2023-09-10",
        "delivery_date": "2023-12-15",
        "risk_rating": "B"
    }
}

# Last updated timestamps for assets
last_updated = {asset_id: datetime.now() for asset_id in RWA_ASSETS}

# Simulated market data update thread
def update_market_data():
    """Simulate market data updates for RWA assets."""
    while True:
        try:
            # Pick a random asset to update
            asset_id = random.choice(list(RWA_ASSETS.keys()))
            asset = RWA_ASSETS[asset_id]
            
            # Update token price with small random change
            price_change_pct = random.uniform(-0.05, 0.05)  # -5% to +5%
            asset["token_price"] *= (1 + price_change_pct)
            asset["token_price"] = round(asset["token_price"], 2)
            
            # Update total valuation
            if "valuation" in asset:
                asset["valuation"] = round(asset["token_price"] * asset["tokens_issued"])
            
            # Update other metrics based on asset type
            if asset_id == "tokenized_real_estate":
                asset["occupancy_rate"] = min(100, max(70, asset["occupancy_rate"] + random.uniform(-2, 2)))
                asset["annual_yield"] = min(12, max(5, asset["annual_yield"] + random.uniform(-0.3, 0.3)))
            elif asset_id == "carbon_credits":
                asset["total_co2_offset"] = asset["credits_issued"]  # Always in sync
            elif asset_id == "commodity_receivables":
                # Simulate price changes due to market conditions
                market_factor = random.uniform(-0.02, 0.02)
                asset["token_price"] *= (1 + market_factor)
                asset["token_price"] = round(asset["token_price"], 2)
            
            # Update timestamp
            last_updated[asset_id] = datetime.now()
            
            # Log the update
            logger.info(f"Updated {asset_id} data: price = {asset['token_price']}")
            
            # If the change is significant, trigger an analysis
            if abs(price_change_pct) > 0.02:  # More than 2% change
                analyze_price_change(asset_id, asset, price_change_pct)
                
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
        
        # Wait for next update (random interval between 30-120 seconds)
        time.sleep(random.randint(30, 120))

def analyze_price_change(asset_id: str, asset: Dict[str, Any], price_change_pct: float):
    """Analyze a significant price change with the AI agent."""
    try:
        # Prepare context data
        context_data = {
            "asset_id": asset_id,
            "asset_data": asset,
            "price_change_pct": price_change_pct * 100,  # Convert to percentage
            "timestamp": datetime.now().isoformat()
        }
        
        # Process with agent
        prompt = f"""
        A significant price change of {price_change_pct:.2%} has occurred for asset {asset_id}.
        
        Please analyze this change and provide:
        1. A brief summary of what happened
        2. Possible reasons for this price movement
        3. Potential implications for investors
        4. Recommendations for monitoring going forward
        
        Keep your analysis factual and data-driven.
        """
        
        response = agent.process(prompt, context_data)
        
        logger.info(f"Price change analysis for {asset_id}: {response['response']}")
        
        # Simulate posting this analysis to the blockchain
        post_analysis_to_blockchain(asset_id, response['response'])
        
    except Exception as e:
        logger.error(f"Error analyzing price change: {e}")

def post_analysis_to_blockchain(asset_id: str, analysis: str):
    """Simulate posting analysis to the blockchain (placeholder)."""
    logger.info(f"Posting analysis for {asset_id} to blockchain (simulated)")
    # In a real implementation, this would use the blockchain client to post data
    # For now, we just log it
    pass

@agent.on_event("rwa_data_request")
def handle_rwa_data_request(event_data):
    """Handle requests for RWA data."""
    logger.info(f"Processing RWA data request: {event_data}")
    
    # Extract asset ID from the request
    asset_id = event_data.get("data", {}).get("asset_id")
    
    if not asset_id or asset_id not in RWA_ASSETS:
        return {
            "error": f"Asset ID {asset_id} not found",
            "available_assets": list(RWA_ASSETS.keys())
        }
    
    # Prepare context data
    context_data = {
        "asset_id": asset_id,
        "asset_data": RWA_ASSETS[asset_id],
        "last_updated": last_updated[asset_id].isoformat()
    }
    
    # Process with agent
    prompt = f"""
    I need information about the real-world asset with ID {asset_id}.
    
    Please provide:
    1. A summary of the asset's key characteristics
    2. Current valuation and token price
    3. Risk assessment and important metrics
    4. Any recent notable changes in the asset's status
    
    Present this data in a structured format that's easy to understand.
    """
    
    response = agent.process(prompt, context_data)
    
    logger.info(f"RWA data provided for {asset_id}")
    return response

@app.route('/api/assets')
def get_assets():
    """API endpoint to get all RWA assets."""
    assets_with_timestamp = {}
    for asset_id, asset_data in RWA_ASSETS.items():
        assets_with_timestamp[asset_id] = {
            **asset_data,
            "last_updated": last_updated[asset_id].isoformat()
        }
    return jsonify(assets_with_timestamp)

@app.route('/api/asset/<asset_id>')
def get_asset(asset_id):
    """API endpoint to get a specific RWA asset."""
    if asset_id not in RWA_ASSETS:
        return jsonify({"error": "Asset not found"}), 404
    
    return jsonify({
        **RWA_ASSETS[asset_id],
        "last_updated": last_updated[asset_id].isoformat()
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_asset():
    """API endpoint to analyze an RWA asset."""
    data = request.get_json()
    asset_id = data.get('asset_id')
    
    if not asset_id or asset_id not in RWA_ASSETS:
        return jsonify({"error": "Invalid asset ID"}), 400
    
    # Create a mock request event
    mock_event = {
        "type": "rwa_data_request",
        "timestamp": datetime.now().timestamp(),
        "data": {
            "asset_id": asset_id,
            "request_type": "analysis",
            "requester": data.get('requester', 'api_user')
        }
    }
    
    # Process the event
    response = handle_rwa_data_request(mock_event)
    
    return jsonify({
        "success": True,
        "asset_id": asset_id,
        "analysis": response['response']
    })

@app.route('/api/simulate_request', methods=['POST'])
def simulate_request():
    """Simulate an on-chain RWA data request."""
    data = request.get_json()
    asset_id = data.get('asset_id')
    
    if not asset_id:
        return jsonify({"error": "Asset ID is required"}), 400
    
    # Create a mock request event
    mock_event = {
        "type": "rwa_data_request",
        "timestamp": datetime.now().timestamp(),
        "data": {
            "asset_id": asset_id,
            "request_type": "query",
            "requester": data.get('requester', 'simulator')
        }
    }
    
    # Process the event
    response = handle_rwa_data_request(mock_event)
    
    return jsonify({
        "success": True,
        "event": mock_event,
        "response": response
    })

if __name__ == '__main__':
    # Start market data update thread
    update_thread = threading.Thread(target=update_market_data, daemon=True)
    update_thread.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
