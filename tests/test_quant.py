from agents.quant import calculate_optimal_rotation
from core.market_god import generate_market_data

def test_calculate_optimal_rotation_normal():
    market_data = generate_market_data("normal")
    result = calculate_optimal_rotation(market_data)
    assert result["suggested_action"] == "NONE"

def test_calculate_optimal_rotation_flash_crash():
    market_data = generate_market_data("flash_crash_eth")
    result = calculate_optimal_rotation(market_data)
    assert result["suggested_action"] == "SWAP_WETH_TO_USDC"

def test_calculate_optimal_rotation_sol_yield():
    market_data = generate_market_data("sol_yield_spike")
    result = calculate_optimal_rotation(market_data)
    assert result["suggested_action"] == "SWAP_WETH_TO_SOL"
