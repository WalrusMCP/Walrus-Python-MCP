"""
Automatic Market Making and Position Adjustment Example

This example demonstrates how to create an AI agent that serves as an
automated market maker that monitors market conditions and adjusts positions
on the Sui blockchain.

To run this example:
1. Set up the required environment variables (OPENAI_API_KEY, WALRUS_SUI_RPC_URL, WALRUS_SUI_PRIVATE_KEY)
2. Run this script: python auto_market_maker.py
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

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "walrus_amm_secret")

# Initialize agent
agent = WalrusAgent(
    agent_name="__AGENT_NAME__",
    storage_granularity=StorageGranularity.HISTORICAL_VERSIONS,
    system_prompt="""You are an Automated Market Making AI assistant. Your role is to:
1. Monitor market conditions and liquidity pools
2. Analyze trading patterns and volatility
3. Recommend position adjustments to optimize returns and minimize impermanent loss
4. Explain market making strategies and pool dynamics

Focus on providing data-driven insights with clear reasoning. Be precise when discussing
financial metrics and explain your logic for any recommendation."""
)

# Sample token pairs and liquidity pools
LIQUIDITY_POOLS = {
    "SUI_USDC": {
        "token_a": {"symbol": "SUI", "name": "Sui", "decimals": 9},
        "token_b": {"symbol": "USDC", "name": "USD Coin", "decimals": 6},
        "pool_address": "0x123456789abcdef123456789abcdef1234567890",
        "reserves_a": 1000000 * 10**9,  # 1M SUI
        "reserves_b": 2000000 * 10**6,  # 2M USDC
        "fee_tier": 0.003,  # 0.3%
        "price_a_in_b": 2.0,  # 1 SUI = 2 USDC
        "tvl_usd": 4000000,  # $4M
        "volume_24h": 500000,  # $500K
        "apy": 12.5
    },
    "SUI_ETH": {
        "token_a": {"symbol": "SUI", "name": "Sui", "decimals": 9},
        "token_b": {"symbol": "ETH", "name": "Ethereum", "decimals": 18},
        "pool_address": "0xabcdef123456789abcdef123456789abcdef1234",
        "reserves_a": 2000000 * 10**9,  # 2M SUI
        "reserves_b": 1000 * 10**18,  # 1K ETH
        "fee_tier": 0.003,  # 0.3%
        "price_a_in_b": 0.0005,  # 1 SUI = 0.0005 ETH
        "tvl_usd": 5000000,  # $5M
        "volume_24h": 750000,  # $750K
        "apy": 15.2
    },
    "ETH_USDC": {
        "token_a": {"symbol": "ETH", "name": "Ethereum", "decimals": 18},
        "token_b": {"symbol": "USDC", "name": "USD Coin", "decimals": 6},
        "pool_address": "0x56789abcdef123456789abcdef123456789abcdef",
        "reserves_a": 1250 * 10**18,  # 1.25K ETH
        "reserves_b": 5000000 * 10**6,  # 5M USDC
        "fee_tier": 0.003,  # 0.3%
        "price_a_in_b": 4000,  # 1 ETH = 4000 USDC
        "tvl_usd": 10000000,  # $10M
        "volume_24h": 2000000,  # $2M
        "apy": 18.7
    }
}

# User positions (in a real application, these would be on-chain)
USER_POSITIONS = {
    "position_1": {
        "owner": "0xuser123456789abcdef123456789abcdef12345678",
        "pool": "SUI_USDC",
        "liquidity": 50000 * 10**18,
        "amount_a": 100000 * 10**9,  # 100K SUI
        "amount_b": 200000 * 10**6,  # 200K USDC
        "apy": 12.5,
        "created_at": "2023-09-15T12:00:00Z",
        "health": "optimal"
    },
    "position_2": {
        "owner": "0xuser123456789abcdef123456789abcdef12345678",
        "pool": "SUI_ETH",
        "liquidity": 30000 * 10**18,
        "amount_a": 150000 * 10**9,  # 150K SUI
        "amount_b": 75 * 10**18,  # 75 ETH
        "apy": 15.2,
        "created_at": "2023-10-01T14:30:00Z",
        "health": "suboptimal"
    }
}

# Market conditions and trends
MARKET_CONDITIONS = {
    "current_time": datetime.now().isoformat(),
    "market_sentiment": "neutral",
    "volatility": "medium",
    "sui_price_trend": "sideways",
    "eth_price_trend": "upward",
    "usdc_stability": "high",
    "liquidity_trend": "increasing",
    "trading_volume_trend": "increasing"
}

# Last updated timestamps
last_updated = {
    "pools": datetime.now(),
    "positions": datetime.now(),
    "market_conditions": datetime.now()
}

# Simulated market update thread
def update_market_data():
    """Simulate market data updates for AMM pools."""
    while True:
        try:
            # Update market conditions
            MARKET_CONDITIONS["current_time"] = datetime.now().isoformat()
            
            # Randomly change market sentiment
            sentiments = ["bearish", "slightly bearish", "neutral", "slightly bullish", "bullish"]
            MARKET_CONDITIONS["market_sentiment"] = random.choice(sentiments)
            
            # Randomly change volatility
            volatilities = ["very low", "low", "medium", "high", "very high"]
            MARKET_CONDITIONS["volatility"] = random.choice(volatilities)
            
            # Update price trends
            trends = ["downward", "slightly downward", "sideways", "slightly upward", "upward"]
            MARKET_CONDITIONS["sui_price_trend"] = random.choice(trends)
            MARKET_CONDITIONS["eth_price_trend"] = random.choice(trends)
            
            # Update all pools
            for pool_id, pool_data in LIQUIDITY_POOLS.items():
                # Simulate price changes
                price_change = random.uniform(-0.05, 0.05)  # -5% to +5%
                pool_data["price_a_in_b"] *= (1 + price_change)
                
                # Update reserves based on price change
                # (In a real AMM, these would follow the constant product formula)
                constant_product = pool_data["reserves_a"] * pool_data["reserves_b"]
                pool_data["reserves_a"] = (constant_product / pool_data["price_a_in_b"]) ** 0.5
                pool_data["reserves_b"] = (constant_product * pool_data["price_a_in_b"]) ** 0.5
                
                # Update TVL and volume
                tvl_change = random.uniform(-0.03, 0.03)  # -3% to +3%
                pool_data["tvl_usd"] *= (1 + tvl_change)
                
                volume_change = random.uniform(-0.1, 0.1)  # -10% to +10%
                pool_data["volume_24h"] *= (1 + volume_change)
                
                # Update APY based on volume and TVL
                pool_data["apy"] = (pool_data["volume_24h"] * pool_data["fee_tier"] * 365) / pool_data["tvl_usd"] * 100
                
                # Clean up numbers for display
                pool_data["price_a_in_b"] = round(pool_data["price_a_in_b"], 6)
                pool_data["tvl_usd"] = round(pool_data["tvl_usd"])
                pool_data["volume_24h"] = round(pool_data["volume_24h"])
                pool_data["apy"] = round(pool_data["apy"], 2)
            
            # Update positions based on new pool data
            for position_id, position in USER_POSITIONS.items():
                pool_id = position["pool"]
                pool = LIQUIDITY_POOLS.get(pool_id)
                
                if pool:
                    # Update position APY to match pool
                    position["apy"] = pool["apy"]
                    
                    # Calculate position health based on impermanent loss risk
                    price_change = abs((pool["price_a_in_b"] * position["amount_b"]) / 
                                      (position["amount_a"]) - 1)
                    
                    if price_change < 0.02:
                        position["health"] = "optimal"
                    elif price_change < 0.05:
                        position["health"] = "good"
                    elif price_change < 0.1:
                        position["health"] = "suboptimal"
                    else:
                        position["health"] = "needs rebalancing"
            
            # Update timestamps
            last_updated["pools"] = datetime.now()
            last_updated["positions"] = datetime.now()
            last_updated["market_conditions"] = datetime.now()
            
            # Log the update
            logger.debug(f"Updated market data at {last_updated['pools']}")
            
            # Check if any position needs attention
            for position_id, position in USER_POSITIONS.items():
                if position["health"] == "needs rebalancing":
                    analyze_position(position_id, position)
                
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
        
        # Wait for next update (random interval between 30-90 seconds)
        time.sleep(random.randint(30, 90))

def analyze_position(position_id: str, position: Dict[str, Any]):
    """Analyze a position that needs attention."""
    try:
        # Get pool data
        pool_id = position["pool"]
        pool = LIQUIDITY_POOLS.get(pool_id, {})
        
        # Prepare context data
        context_data = {
            "position_id": position_id,
            "position": position,
            "pool": pool,
            "market_conditions": MARKET_CONDITIONS,
            "timestamp": datetime.now().isoformat()
        }
        
        # Process with agent
        prompt = f"""
        Position {position_id} in pool {pool_id} needs rebalancing. 
        
        Current position status:
        - Health: {position["health"]}
        - Current APY: {position["apy"]}%
        - Token A: {position["amount_a"] / 10**LIQUIDITY_POOLS[pool_id]["token_a"]["decimals"]} {LIQUIDITY_POOLS[pool_id]["token_a"]["symbol"]}
        - Token B: {position["amount_b"] / 10**LIQUIDITY_POOLS[pool_id]["token_b"]["decimals"]} {LIQUIDITY_POOLS[pool_id]["token_b"]["symbol"]}
        
        Please analyze this position and recommend an optimal rebalancing strategy:
        1. What's causing the position to need rebalancing?
        2. What specific actions should be taken to optimize it?
        3. What's the expected outcome after rebalancing?
        4. Are there any risks to be aware of with this approach?
        
        Be specific with your recommendations, including suggested percentage adjustments or target ratios.
        """
        
        response = agent.process(prompt, context_data)
        
        logger.info(f"Position analysis for {position_id}: {response['response']}")
        
        # In a real implementation, we might execute the rebalancing automatically
        # based on the AI's recommendation
        return response
    except Exception as e:
        logger.error(f"Error analyzing position: {e}")
        return {"error": str(e)}

@agent.on_event("liquidity_imbalance")
def handle_liquidity_imbalance(event_data):
    """Handle liquidity imbalance events from the blockchain."""
    logger.info(f"Processing liquidity imbalance event: {event_data}")
    
    # Extract pool ID from the event
    pool_id = event_data.get("data", {}).get("pool_id")
    
    if not pool_id or pool_id not in LIQUIDITY_POOLS:
        return {
            "error": f"Pool ID {pool_id} not found",
            "available_pools": list(LIQUIDITY_POOLS.keys())
        }
    
    # Prepare context data
    context_data = {
        "pool_id": pool_id,
        "pool_data": LIQUIDITY_POOLS[pool_id],
        "event_data": event_data,
        "market_conditions": MARKET_CONDITIONS
    }
    
    # Process with agent
    prompt = f"""
    A liquidity imbalance has been detected in pool {pool_id}.
    
    Please analyze this situation and provide:
    1. An assessment of the current pool state
    2. The likely causes of this imbalance
    3. Recommendations for liquidity providers
    4. Potential market implications
    
    Make your analysis data-driven and actionable for liquidity providers.
    """
    
    response = agent.process(prompt, context_data)
    
    logger.info(f"Liquidity imbalance analysis provided for {pool_id}")
    return response

@app.route('/api/pools')
def get_pools():
    """API endpoint to get all liquidity pools."""
    return jsonify({
        "pools": LIQUIDITY_POOLS,
        "last_updated": last_updated["pools"].isoformat()
    })

@app.route('/api/pool/<pool_id>')
def get_pool(pool_id):
    """API endpoint to get a specific liquidity pool."""
    if pool_id not in LIQUIDITY_POOLS:
        return jsonify({"error": "Pool not found"}), 404
    
    return jsonify({
        "pool": LIQUIDITY_POOLS[pool_id],
        "last_updated": last_updated["pools"].isoformat()
    })

@app.route('/api/positions')
def get_positions():
    """API endpoint to get all user positions."""
    return jsonify({
        "positions": USER_POSITIONS,
        "last_updated": last_updated["positions"].isoformat()
    })

@app.route('/api/position/<position_id>')
def get_position(position_id):
    """API endpoint to get a specific user position."""
    if position_id not in USER_POSITIONS:
        return jsonify({"error": "Position not found"}), 404
    
    return jsonify({
        "position": USER_POSITIONS[position_id],
        "last_updated": last_updated["positions"].isoformat()
    })

@app.route('/api/market_conditions')
def get_market_conditions():
    """API endpoint to get current market conditions."""
    return jsonify({
        "market_conditions": MARKET_CONDITIONS,
        "last_updated": last_updated["market_conditions"].isoformat()
    })

@app.route('/api/analyze_position/<position_id>')
def api_analyze_position(position_id):
    """API endpoint to analyze a position."""
    if position_id not in USER_POSITIONS:
        return jsonify({"error": "Position not found"}), 404
    
    response = analyze_position(position_id, USER_POSITIONS[position_id])
    
    return jsonify({
        "success": True,
        "position_id": position_id,
        "analysis": response['response'] if 'response' in response else response
    })

@app.route('/api/simulate_imbalance', methods=['POST'])
def simulate_imbalance():
    """Simulate a liquidity imbalance event."""
    data = request.get_json()
    pool_id = data.get('pool_id')
    
    if not pool_id or pool_id not in LIQUIDITY_POOLS:
        return jsonify({"error": "Invalid pool ID"}), 400
    
    # Create a mock imbalance event
    mock_event = {
        "type": "liquidity_imbalance",
        "timestamp": datetime.now().timestamp(),
        "data": {
            "pool_id": pool_id,
            "severity": data.get('severity', 'moderate'),
            "imbalance_ratio": random.uniform(1.2, 1.5),
            "detected_by": data.get('detector', 'monitoring_service')
        }
    }
    
    # Process the event
    response = handle_liquidity_imbalance(mock_event)
    
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
