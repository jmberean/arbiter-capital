// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Script, console2} from "forge-std/Script.sol";
import {ArbiterReceipt} from "../contracts/ArbiterReceipt.sol";

/// @notice Deploy the ArbiterReceipt soulbound ERC-721 contract.
///
/// Usage:
///   forge script script/DeployArbiterReceipt.s.sol \
///       --rpc-url $SEPOLIA_RPC \
///       --private-key $DEPLOYER_KEY \
///       --broadcast \
///       --verify
///
/// Required env vars: SAFE_ADDRESS, EXECUTOR_PRIVATE_KEY
contract DeployArbiterReceipt is Script {
    function run() external returns (address receipt) {
        address safe     = vm.envAddress("SAFE_ADDRESS");
        address executor = vm.addr(vm.envUint("EXECUTOR_PRIVATE_KEY"));

        console2.log("Deploying ArbiterReceipt...");
        console2.log("  Safe (token recipient):", safe);
        console2.log("  Executor (minter):     ", executor);

        vm.startBroadcast();
        receipt = address(new ArbiterReceipt(safe, executor));
        vm.stopBroadcast();

        console2.log("\nArbiterReceipt deployed:", receipt);
        console2.log("\nAdd to .env:");
        console2.log("  ARBITER_RECEIPT_NFT=", vm.toString(receipt));
    }
}
