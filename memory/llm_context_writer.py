"""Builds an LLMContext receipt and persists it to 0G.

Determinism guarantees:
  - parsed_obj is dumped with exclude_none=True so unset fields don't enter the hash
  - schema is canonicalized with sort_keys + tight separators (matches 0G chain canonicalization)
  - context_hash is computed over the receipt body INCLUDING the parsed/schema hashes,
    so any field drift in the LLM call is detectable.
"""
import json
import time
import uuid

from eth_utils import keccak

from core.models import LLMContext
from memory.memory_manager import MemoryManager


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def capture_and_persist(*, agent, proposal_id, iteration, model_id, temperature, seed,
                        schema, schema_name, system_prompt, messages, response_raw,
                        parsed_obj, tools_invoked) -> tuple[str, str]:
    """Build LLMContext, write to 0G, return (context_hash, 0g_tx_hash)."""
    if hasattr(parsed_obj, "model_dump"):
        parsed_dict = parsed_obj.model_dump(exclude_none=True)
    elif isinstance(parsed_obj, dict):
        parsed_dict = parsed_obj
    else:
        parsed_dict = {"value": str(parsed_obj)}

    parsed_canonical = _canonical(parsed_dict)
    schema_canonical = _canonical(schema)

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
        "system_prompt": system_prompt or "",
        "messages": messages or [],
        "response_raw": response_raw or "",
        "response_parsed_hash": "0x" + keccak(parsed_canonical).hex(),
        "tools_invoked": tools_invoked or [],
    }

    canonical = _canonical(body)
    body["context_hash"] = "0x" + keccak(canonical).hex()
    ctx = LLMContext(**body)
    tx_hash = MemoryManager().write_artifact("LLMContext", ctx.model_dump())
    return body["context_hash"], tx_hash
