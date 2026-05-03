import os
from eth_account import Account
from dotenv import load_dotenv

def generate_node_keys():
    node_ids = ["QUANT", "PATRIARCH", "EXEC", "KEEPERHUB", "WATCHDOG"]
    keys = {}
    for nid in node_ids:
        acct = Account.create()
        keys[f"AXL_NODE_KEY_{nid}"] = acct.key.hex()
    return keys

def update_env(new_keys):
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    # Update existing or add new
    for key, val in new_keys.items():
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={val}\n"
                found = True
                break
        if not found:
            lines.append(f"{key}={val}\n")
    
    # Ensure DEMO_MODE=1
    demo_found = False
    for i, line in enumerate(lines):
        if line.startswith("DEMO_MODE="):
            lines[i] = "DEMO_MODE=1\n"
            demo_found = True
            break
    if not demo_found:
        lines.append("DEMO_MODE=1\n")

    with open(env_path, "w") as f:
        f.writelines(lines)
    print("Updated .env with node keys and set DEMO_MODE=1")

if __name__ == "__main__":
    keys = generate_node_keys()
    update_env(keys)
