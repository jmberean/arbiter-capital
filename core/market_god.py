import json
import time
import random

def generate_market_data(scenario: str = "normal"):
    """
    Generates synthetic market data to inject into the Quant agent.
    
    Args:
        scenario: 'normal', 'flash_crash_eth', 'sol_yield_spike'
    """
    
    base_data = {
        "timestamp": int(time.time()),
        "assets": {
            "WETH": {"price": 3500.0, "volatility_48h": 0.04, "staking_yield": 0.03},
            "SOL": {"price": 150.0, "volatility_48h": 0.06, "staking_yield": 0.07},
            "USDC": {"price": 1.0, "volatility_48h": 0.001, "staking_yield": 0.04}
        },
        "market_sentiment": "neutral"
    }

    if scenario == "flash_crash_eth":
        base_data["assets"]["WETH"]["price"] = 2975.0  # 15% drop
        base_data["assets"]["WETH"]["volatility_48h"] = 0.25 # Huge volatility spike
        base_data["market_sentiment"] = "panic"
        base_data["events"] = ["Flash crash detected on major CEXs for ETH."]
        print("⚡ MARKET GOD INJECTION: Flash crash on ETH initiated.")

    elif scenario == "sol_yield_spike":
        base_data["assets"]["SOL"]["staking_yield"] = 0.12 # Yield jump
        base_data["market_sentiment"] = "greedy"
        base_data["events"] = ["New SOL staking derivative launched with high liquidity incentives."]
        print("📈 MARKET GOD INJECTION: SOL yield spike initiated.")
        
    return base_data

if __name__ == "__main__":
    # Test injection
    print(json.dumps(generate_market_data("flash_crash_eth"), indent=2))
