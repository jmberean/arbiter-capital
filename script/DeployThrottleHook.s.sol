// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Script, console2} from "forge-std/Script.sol";
import {ArbiterThrottleHook} from "../contracts/ArbiterThrottleHook.sol";
import {IPoolManager} from "v4-core/interfaces/IPoolManager.sol";

/// @notice Deploy ArbiterThrottleHook at a CREATE2 address with correct permission bits.
///
/// Prerequisites:
///   1. Run HookMiner.s.sol first to find a valid salt.
///   2. Set HOOK_SALT and ARBITER_THROTTLE_HOOK (expected address) in .env.
///
/// Usage:
///   forge script script/DeployThrottleHook.s.sol \
///       --rpc-url $SEPOLIA_RPC \
///       --private-key $DEPLOYER_KEY \
///       --broadcast \
///       --verify
///
/// After deployment, verify manually if --verify fails:
///   forge verify-contract $ARBITER_THROTTLE_HOOK \
///       contracts/ArbiterThrottleHook.sol:ArbiterThrottleHook \
///       --constructor-args $(cast abi-encode "constructor(address,address,uint32,uint32,uint128)" \
///           $V4_POOL_MANAGER $SAFE_ADDRESS 60 3600 10000000000000000000) \
///       --rpc-url $SEPOLIA_RPC \
///       --etherscan-api-key $ETHERSCAN_API_KEY
contract DeployThrottleHook is Script {
    // CREATE2_FACTORY (0x4e59b44847b379578588920cA78FbF26c0B4956C) is inherited from forge-std/Script.
    uint160 constant FLAGS     = (1 << 7) | (1 << 6); // BEFORE_SWAP | AFTER_SWAP = 0x00C0
    uint160 constant FLAG_MASK = (1 << 14) - 1;

    function run() external returns (address hook) {
        address poolManager = vm.envAddress("V4_POOL_MANAGER");
        address safe         = vm.envAddress("SAFE_ADDRESS");
        bytes32 salt         = vm.envBytes32("HOOK_SALT");
        uint32  cooldown     = uint32(vm.envOr("HOOK_COOLDOWN_SECONDS", uint256(60)));
        uint32  window_      = uint32(vm.envOr("HOOK_WINDOW_SECONDS",   uint256(3600)));
        uint128 maxNotional  = uint128(vm.envOr("HOOK_MAX_NOTIONAL",    uint256(10 ether)));

        // Pre-flight: confirm the mined salt still yields the correct flags
        bytes32 initCodeHash = keccak256(abi.encodePacked(
            type(ArbiterThrottleHook).creationCode,
            abi.encode(IPoolManager(poolManager), safe, cooldown, window_, maxNotional)
        ));
        address expected = address(uint160(uint256(keccak256(
            abi.encodePacked(bytes1(0xff), CREATE2_FACTORY, salt, initCodeHash)
        ))));
        require(
            uint160(expected) & FLAG_MASK == FLAGS,
            "Salt invalid: low-14-bits != 0x00C0. Re-run HookMiner."
        );
        console2.log("Salt pre-flight OK. Expected hook:", expected);

        vm.startBroadcast();
        // Forge routes `new Contract{salt: s}` through CREATE2_FACTORY, matching the mined address.
        hook = address(new ArbiterThrottleHook{salt: salt}(
            IPoolManager(poolManager),
            safe,
            cooldown,
            window_,
            maxNotional
        ));
        vm.stopBroadcast();

        require(hook == expected, string(abi.encodePacked(
            "Address mismatch! got=", vm.toString(hook), " want=", vm.toString(expected)
        )));

        console2.log("ArbiterThrottleHook deployed:", hook);
        console2.log("  Permission bits (& 0x3FFF):", uint160(hook) & FLAG_MASK);
        console2.log("\nAdd to .env:");
        console2.log("  ARBITER_THROTTLE_HOOK=", vm.toString(hook));
    }
}
