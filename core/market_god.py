import json
import time
import random

def generate_market_data(scenario: str = "normal"):
    """
    Generates high-fidelity synthetic market data with specific DeFi instruments.
    """
    
    base_data = {
        "timestamp": int(time.time()),
        "network": {
            "gas_price_gwei": 25.0,
            "congestion_level": "low"
        },
        "assets": {
            "WETH": {"price": 3500.0, "volatility_48h": 0.04, "staking_yield": 0.03, "safety_score": 9.5},
            "stETH": {"price": 3510.0, "volatility_48h": 0.04, "staking_yield": 0.042, "safety_score": 9.2}, # LST
            "SOL": {"price": 150.0, "volatility_48h": 0.06, "staking_yield": 0.07, "safety_score": 8.0},
            "USDC": {"price": 1.0, "volatility_48h": 0.001, "staking_yield": 0.04, "safety_score": 9.9},
            "PENDLE_PT_USDC": {"price": 0.92, "volatility_48h": 0.01, "implied_yield": 0.14, "safety_score": 8.5} # Yield Trading
        },
        "market_sentiment": "neutral",
        "events": []
    }

    if scenario == "pendle_yield_arbitrage":
        # Implied yield on Pendle USDC jumps to 22%
        base_data["assets"]["PENDLE_PT_USDC"]["implied_yield"] = 0.22
        base_data["assets"]["PENDLE_PT_USDC"]["price"] = 0.88 # Price drops as yield rises
        base_data["events"].append("Pendle Market: Massive yield spread detected on PT-USDC pool.")
        print("📈 MARKET GOD INJECTION: Pendle Yield Arbitrage opportunity identified.")

    elif scenario == "lst_expansion":
        # stETH yield becomes significantly better than base staking
        base_data["assets"]["stETH"]["staking_yield"] = 0.065
        base_data["events"].append("Lido protocol upgrades: stETH rewards increased.")
        print("💧 MARKET GOD INJECTION: LST Yield Expansion initiated.")
        
    elif scenario == "protocol_hack":
        base_data["assets"]["SOL"]["safety_score"] = 2.0
        base_data["market_sentiment"] = "panic"
        base_data["events"].append("CRITICAL: Major Solana Staking Protocol exploited.")
        
    elif scenario == "flash_crash_eth":
        base_data["assets"]["WETH"]["price"] = 2800.0
        base_data["assets"]["WETH"]["volatility_48h"] = 0.45
        base_data["market_sentiment"] = "panic"
        base_data["events"].append("Flash Crash: ETH dropped 20% in 15 minutes.")

    elif scenario == "sol_yield_spike" or scenario == "cross_chain_alpha":
        base_data["assets"]["SOL"]["staking_yield"] = 0.12
        base_data["market_sentiment"] = "greedy"
        base_data["events"].append("Solana Surge: Cross-chain liquidity incentives live on SOL.")

    elif scenario == "gas_war":
        base_data["network"]["gas_price_gwei"] = 850.0
        base_data["assets"]["WETH"]["volatility_48h"] = 0.38
        base_data["market_sentiment"] = "panic"
        base_data["events"].append("Gas War: Network congestion spike to 850 gwei. ETH volatility elevated.")
        
    return base_data

if __name__ == "__main__":
    import sys
    scn = sys.argv[1] if len(sys.argv) > 1 else "normal"
    print(json.dumps(generate_market_data(scn), indent=2))
