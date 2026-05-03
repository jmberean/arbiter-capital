import sqlite3
import time
import json

def poll():
    conn = sqlite3.connect('axl_network.db')
    deadline = time.time() + 180
    last_id = 0
    
    print("Monitoring AXL bus for trade progress...")
    
    while time.time() < deadline:
        try:
            cursor = conn.execute(
                "SELECT id, topic, payload FROM messages WHERE id > ? AND topic IN "
                "('EXECUTION_SUCCESS', 'EXECUTION_FAILURE', 'ATTACK_REJECTED', 'PROPOSAL_EVALUATIONS', 'PROPOSALS') "
                "ORDER BY id ASC", (last_id,)
            )
            rows = cursor.fetchall()
            for row_id, topic, payload in rows:
                last_id = row_id
                data = json.loads(payload)
                
                if topic == 'PROPOSALS':
                    print(f"  [+] New Proposal: {data.get('proposal_id')} ({data.get('action')})")
                
                elif topic == 'PROPOSAL_EVALUATIONS':
                    status = data.get('consensus_status')
                    print(f"  [?] Evaluation: {status}")
                    if status == 'REJECTED':
                        print(f"      Reason: {data.get('rationale')}")
                
                elif topic == 'ATTACK_REJECTED':
                    print(f"  [!] Attack Rejected: {data.get('rejection_reason')}")
                
                elif topic == 'EXECUTION_SUCCESS':
                    tx_hash = data.get('tx_hash')
                    print(f"\n  [✓] EXECUTION SUCCESSFUL!")
                    print(f"      TX Hash: {tx_hash}")
                    print(f"      Etherscan: https://sepolia.etherscan.io/tx/{tx_hash}")
                    return True
                
                elif topic == 'EXECUTION_FAILURE':
                    print(f"\n  [✗] EXECUTION FAILED")
                    print(f"      Detail: {data.get('detail')}")
                    return False
        except Exception as e:
            print(f"Error polling: {e}")
            
        time.sleep(5)
    
    print("\n[!] Timeout reached.")
    return False

if __name__ == "__main__":
    poll()
