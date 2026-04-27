import json, time, uuid
from eth_utils import keccak
from core.models import LLMContext
from memory.memory_manager import MemoryManager

def capture_and_persist(*, agent, proposal_id, iteration, model_id, temperature, seed,
                       schema, schema_name, system_prompt, messages, response_raw, parsed_obj,
                       tools_invoked) -> tuple[str, str]:
    """Build LLMContext, write to 0G, return (context_hash, 0g_tx_hash)."""
    parsed_canonical = json.dumps(parsed_obj.model_dump(), sort_keys=True, separators=(",",":")).encode()
    schema_canonical = json.dumps(schema, sort_keys=True, separators=(",",":")).encode()
    body = {
        "schema_version": 1,
        "call_id": uuid.uuid4().hex,
        "invoking_agent": agent,
        "invoked_at": time.time(),
        "proposal_id": proposal_id,
        "iteration": iteration,
        "model_id": model_id,
        "temperature": temperature,
        "seed": seed,
        "structured_output_schema_hash": "0x" + keccak(schema_canonical).hex(),
        "structured_output_schema_name": schema_name,
        "system_prompt": system_prompt,
        "messages": messages,
        "response_raw": response_raw,
        "response_parsed_hash": "0x" + keccak(parsed_canonical).hex(),
        "tools_invoked": tools_invoked,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",",":")).encode()
    body["context_hash"] = "0x" + keccak(canonical).hex()
    ctx = LLMContext(**body)
    mm = MemoryManager()
    tx_hash = mm.write_artifact("LLMContext", ctx.model_dump())
    return body["context_hash"], tx_hash
