from core.market_god import generate_market_data

def test_generate_market_data_normal():
    data = generate_market_data("normal")
    assert "assets" in data
    assert data["assets"]["WETH"]["price"] == 3500.0
    assert data["market_sentiment"] == "neutral"

def test_generate_market_data_flash_crash():
    data = generate_market_data("flash_crash_eth")
    assert data["assets"]["WETH"]["price"] < 3500.0
    assert data["market_sentiment"] == "panic"
    assert data["assets"]["WETH"]["volatility_48h"] > 0.1

def test_generate_market_data_sol_yield():
    data = generate_market_data("sol_yield_spike")
    assert data["assets"]["SOL"]["staking_yield"] > 0.1
    assert data["market_sentiment"] == "greedy"
