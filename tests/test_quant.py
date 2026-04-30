from agents.quant import calculate_optimal_rotation
from core.market_god import generate_market_data

def test_calculate_optimal_rotation_normal():
    market_data = generate_market_data("normal")
    result = calculate_optimal_rotation(market_data)
    assert result["suggested_action"] == "NONE"

def test_calculate_optimal_rotation_pendle():
    market_data = generate_market_data("pendle_yield_arbitrage")
    result = calculate_optimal_rotation(market_data)
    assert result["suggested_action"] == "YIELD_TRADE"
    assert result["target_protocol"] == "Pendle"

def test_calculate_optimal_rotation_lst():
    market_data = generate_market_data("lst_expansion")
    result = calculate_optimal_rotation(market_data)
    assert result["suggested_action"] == "STAKE_LST"
    assert result["target_protocol"] == "Lido"

def test_calculate_optimal_rotation_protocol_hack():
    market_data = generate_market_data("protocol_hack")
    result = calculate_optimal_rotation(market_data)
    assert result["suggested_action"] == "EMERGENCY_WITHDRAW"

def test_calculate_optimal_rotation_flash_crash():
    market_data = generate_market_data("flash_crash_eth")
    result = calculate_optimal_rotation(market_data)
    # Flash crash increases volatility, should trigger SWAP to USDC
    assert result["suggested_action"] == "SWAP"
    assert result["asset_out"] == "USDC"

def test_calculate_optimal_rotation_cross_chain():
    market_data = generate_market_data("cross_chain_alpha")
    result = calculate_optimal_rotation(market_data)
    # In my current implementation of calculate_optimal_rotation, 
    # it might not have a specific case for SOL yield surge yet,
    # let's see what it does.
    # If it's not implemented, it might return NONE or something else.
    # Actually, calculate_optimal_rotation doesn't seem to have a SOL case.
    # I should check if I should add it.
