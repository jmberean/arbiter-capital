# KeeperHub Builder Feedback — Arbiter Capital

**Submitted:** 2026-05-05
**Project:** Arbiter Capital (ETHGlobal Open Agents 2026)
**Total integration time:** ~3 days (Days 5–7 of our sprint)
**Build context:** Multi-agent DeFi treasury manager. We integrated KeeperHub in two distinct ways:
  1. **Focus Area 1 (MCP client):** Patriarch agent calls `simulate_safe_tx` via MCP before countersigning a proposal. This gives us a fork-accurate revert check before any gas is spent.
  2. **Focus Area 2 (LangChain bridge):** `langchain_keeperhub.py` wraps both `simulate_safe_tx` and `execute_safe_transaction` as `BaseTool` subclasses reusable by any LangGraph project.

---

## Friction Point #1: MCP stdio transport hangs silently when binary path is wrong

**Date encountered:** 2026-05-01
**Affected component:** MCP `stdio_client` / KeeperHub server binary startup
**Reproduction:**
1. Set `KEEPERHUB_SERVER_PATH=/wrong/path/keeperhub-mcp`
2. Call `await session.initialize()` inside `mcp.client.stdio.stdio_client`
**Expected:** An `OSError` or `FileNotFoundError` is raised immediately.
**Actual:** `asyncio.create_subprocess_exec` spawns a process that silently fails to exec; the MCP client hangs indefinitely waiting for an `initialize` response that never arrives. No exception is surfaced; the coroutine only terminates when the caller's outer timeout fires.
**Workaround:** Wrap every `_mcp_call` in `asyncio.wait_for(..., timeout=8.0)` and check `KEEPERHUB_SERVER_PATH` existence at startup.
**Suggested fix:** `stdio_client` should set a short deadline (e.g. 5 s) on the `initialize` handshake and raise `ConnectionError` if it is not received. Alternatively, document that callers must validate the binary path before calling `stdio_client`.

---

## Friction Point #2: No built-in reconnection for dropped MCP server connections

**Date encountered:** 2026-05-02
**Affected component:** `mcp.ClientSession` lifecycle management
**Reproduction:**
1. Start KeeperHub MCP server.
2. Kill the server process mid-session.
3. Attempt another `session.call_tool(...)`.
**Expected:** `ClientSession` raises a recoverable exception; the caller can reconnect.
**Actual:** `call_tool` raises `BrokenPipeError` or `EOFError`; there is no built-in retry or reconnect mechanism in the MCP SDK. Our daemon must catch the error, tear down the entire `stdio_client` context manager, and re-enter it for the next call — adding ~300ms latency per reconnect.
**Workaround:** Wrap each MCP call in a fresh `async with stdio_client(...) as ...: async with ClientSession(...) as ...:` block (i.e. no persistent session). This is expensive but safe.
**Suggested fix:** Add a `ClientSession.reconnect()` method or a `persistent=True` flag that automatically re-spawns the subprocess and re-issues `initialize` on pipe failure, with configurable backoff.

---

## Friction Point #3: `simulate_safe_tx` result schema is not versioned

**Date encountered:** 2026-05-03
**Affected component:** `simulate_safe_tx` MCP tool response
**Reproduction:**
1. Call `simulate_safe_tx` and inspect the returned JSON.
**Expected:** Response includes a `schema_version` field so consumers can handle breaking changes gracefully.
**Actual:** No version field. Our `SimulationResult` Pydantic model parsed the response fine during the hackathon, but any change to the response shape (e.g. renaming `revert_reason` to `revert_data`) will silently produce `None` fields rather than a validation error.
**Workaround:** We pinned our Pydantic model to exactly the fields we observed and added `model_config = ConfigDict(extra="ignore")`.
**Suggested fix:** Add `"schema_version": 1` to all tool responses. Increment on breaking changes. Document the schema in the KeeperHub MCP server README.

---

## Friction Point #4: KeeperHub Module enable-tx requires manual nonce management

**Date encountered:** 2026-05-02
**Affected component:** Safe module enablement workflow
**Reproduction:**
1. Call `enableModule(KEEPERHUB_ADDR)` on a 2-of-2 Safe.
2. Attempt to use `safe-eth-py` to build the multisig tx.
**Expected:** KeeperHub documentation shows a one-liner to enable the module via their SDK.
**Actual:** Documentation only covers the "module already enabled" happy path. There is no helper to build, sign, and submit the `enableModule` Safe transaction. We had to write `scripts/enable_keeperhub_module.py` from scratch using `safe-eth-py`, coordinate two private keys across two team members, and submit manually.
**Workaround:** Custom script using `safe-eth-py` (`build_multisig_tx` + `get_transaction_hash` + dual `unsafe_sign_hash`).
**Suggested fix:** Provide a `keeperhub-cli enable-module --safe <addr> --key <hex>` command, or at minimum a code snippet in the "Getting Started" doc that shows how to enable the module on a threshold-N Safe.

---

## Friction Point #5: Attestor signature format not documented for off-chain verifiers

**Date encountered:** 2026-05-03
**Affected component:** `simulator_signature` field in `SimulationResult`
**Reproduction:**
1. Receive a `SimulationResult` from `simulate_safe_tx`.
2. Attempt to verify `simulator_signature` using `eth_account._recover_hash`.
**Expected:** Documentation states the exact signing scheme (e.g. "raw keccak256 of the JSON body, signed with `Account.unsafe_sign_hash`").
**Actual:** No documentation on what was signed. We had to experimentally determine the signed payload by testing different encodings (raw bytes, EIP-191 prefix, RLP, raw JSON) until recovery of our own `KEEPERHUB_ATTESTOR_KEY` succeeded.
**Workaround:** We settled on `keccak256(json.dumps(result_without_sig, sort_keys=True))` which matched, but this is fragile.
**Suggested fix:** Document the attestor signature scheme in the MCP server README: what bytes are signed, how they are encoded, how to recover the attestor address. Provide a reference Python snippet.

---

## Documentation Gap #1: "LangChain Integration" section missing from official docs

**Page URL:** https://docs.keeperhub.xyz (general docs, as accessed 2026-05-01)
**What was missing:** There is no "LangChain / LangGraph integration" section. Focus Area 2 of the KeeperHub bounty explicitly rewards "bridges/plugins for agent frameworks like LangChain," but the docs only show raw MCP usage.
**What we had to figure out:** How to wrap KeeperHub tools as `BaseTool` subclasses that work with `ainvoke`, handle async lifecycle, and expose correct `args_schema`.
**Suggested doc addition:**
> **LangChain integration** — KeeperHub MCP tools can be wrapped as `langchain_core.tools.BaseTool` subclasses. Each tool call should open a fresh `stdio_client` session (connection pooling is not yet supported). Use `asyncio.wait_for(..., timeout=8.0)` to guard against startup hangs. See [Arbiter Capital's `langchain_keeperhub.py`](https://github.com/arbiter-capital/arbiter-capital/blob/main/langchain_keeperhub.py) for a reference implementation.

---

## Positive Notes (what worked unusually well)

- **MCP tool discovery:** `session.list_tools()` worked perfectly out of the box; we auto-generate our tool registry from it.
- **Fork simulation accuracy:** `simulate_safe_tx` correctly detected a reentrancy revert that our own Tenderly fork missed due to a stale state issue. The accuracy gain was genuine and demo-able.
- **Reliability during the hackathon:** The MCP server did not crash once over a 24h dev session, despite our processes restarting repeatedly.

---

## Asks for v-next

- Persistent `ClientSession` with auto-reconnect (replaces per-call stdio spawning).
- Versioned response schemas for all tools.
- `keeperhub-cli enable-module` CLI helper.
- A `langchain-keeperhub` PyPI package with the `BaseTool` wrappers pre-built (we'd contribute ours).
- Webhook / push mode for `SIM_ORACLE_RESULT` so Patriarch doesn't need to poll.
