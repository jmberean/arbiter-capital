import logging
import sys
from core.market_god import generate_market_data
from core.network import MockAXLNode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MarketGod")

def inject(scenario: str = "flash_crash_eth"):
    logger.info("Initializing Market God Injector...")
    axl_node = MockAXLNode(node_id="MarketGod")
    
    # Clear the network for a fresh demo run
    axl_node.clear_network()
    logger.info("Cleared existing AXL network state.")

    market_data = generate_market_data(scenario)
    
    logger.info(f"Injecting market data scenario: {scenario}")
    axl_node.publish(topic="MARKET_DATA", payload=market_data)
    logger.info("Injection complete. Check Quant and Patriarch terminals.")

if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "flash_crash_eth"
    inject(scenario)
