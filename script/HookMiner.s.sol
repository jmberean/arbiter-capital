// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Script, console2} from "forge-std/Script.sol";
import {ArbiterThrottleHook} from "../contracts/ArbiterThrottleHook.sol";
import {IPoolManager} from "v4-core/interfaces/IPoolManager.sol";

/// @notice Off-chain salt miner for ArbiterThrottleHook.
///
/// Usage (no --broadcast needed):
///   forge script script/HookMiner.s.sol \
///       --rpc-url $SEPOLIA_RPC -vvv
///
/// Copy the printed HOOK_SALT and ARBITER_THROTTLE_HOOK into .env,
/// then run DeployThrottleHook.s.sol with --broadcast --verify.
contract HookMinerScript is Script {
    // CREATE2_FACTORY (0x4e59b44847b379578588920cA78FbF26c0B4956C) is inherited from forge-std/Script.
    // Forge routes `new Contract{salt: s}(...)` through this factory when broadcasting.

    // Required hook address flags: BEFORE_SWAP (bit 7) | AFTER_SWAP (bit 6) = 0x00C0
    uint160 constant FLAGS     = (1 << 7) | (1 << 6);
    uint160 constant FLAG_MASK = (1 << 14) - 1; // all 14 permission bits

    function run() external {
        address poolManager = vm.envAddress("V4_POOL_MANAGER");
        address safe         = vm.envAddress("SAFE_ADDRESS");
        uint32  cooldown     = uint32(vm.envOr("HOOK_COOLDOWN_SECONDS", uint256(60)));
        uint32  window_      = uint32(vm.envOr("HOOK_WINDOW_SECONDS",   uint256(3600)));
        uint128 maxNotional  = uint128(vm.envOr("HOOK_MAX_NOTIONAL",    uint256(10 ether)));

        bytes memory initCode = abi.encodePacked(
            type(ArbiterThrottleHook).creationCode,
            abi.encode(IPoolManager(poolManager), safe, cooldown, window_, maxNotional)
        );
        bytes32 initCodeHash = keccak256(initCode);

        console2.log("=== ArbiterThrottleHook Salt Miner ===");
        console2.log("  CREATE2 factory:", CREATE2_FACTORY);
        console2.log("  Target flags:    0x00C0 (BEFORE_SWAP | AFTER_SWAP)");
        console2.log("  PoolManager:    ", poolManager);
        console2.log("  Safe:           ", safe);
        console2.log("  Cooldown (s):   ", cooldown);
        console2.log("  Window (s):     ", window_);
        console2.log("  MaxNotional:    ", maxNotional);

        uint256 salt = 0;
        address hookAddr;
        while (true) {
            unchecked { salt++; }
            hookAddr = address(uint160(uint256(keccak256(
                abi.encodePacked(bytes1(0xff), CREATE2_FACTORY, bytes32(salt), initCodeHash)
            ))));
            if (uint160(hookAddr) & FLAG_MASK == FLAGS) break;
            if (salt % 10_000 == 0) console2.log("  ... tried", salt, "salts");
        }

        console2.log("\n=== SALT FOUND ===");
        console2.log("  Iterations:          ", salt);
        console2.log("  Salt (bytes32):      ", vm.toString(bytes32(salt)));
        console2.log("  Hook address:        ", vm.toString(hookAddr));
        console2.log("  Low-14-bits (=0xC0): ", uint160(hookAddr) & FLAG_MASK);
        console2.log("\nAdd to .env:");
        console2.log("  HOOK_SALT=", vm.toString(bytes32(salt)));
        console2.log("  ARBITER_THROTTLE_HOOK=", vm.toString(hookAddr));
    }
}
