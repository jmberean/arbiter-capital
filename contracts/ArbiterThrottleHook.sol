// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {BaseHook} from "v4-periphery/utils/BaseHook.sol";
import {IPoolManager} from "v4-core/interfaces/IPoolManager.sol";
import {Hooks} from "v4-core/libraries/Hooks.sol";
import {PoolKey} from "v4-core/types/PoolKey.sol";
import {BeforeSwapDelta, BeforeSwapDeltaLibrary} from "v4-core/types/BeforeSwapDelta.sol";
import {BalanceDelta} from "v4-core/types/BalanceDelta.sol";

/// @title ArbiterThrottleHook
/// @notice Per-pool throttle for the Arbiter Safe: enforces a cooldown between
///         swaps and a rolling notional cap per window. Reverts in beforeSwap if
///         either limit is exceeded; afterSwap accumulates notional usage.
/// @dev    Only `arbiterSafe` is throttled; all other senders pass through.
contract ArbiterThrottleHook is BaseHook {
    /// @notice The Safe whose swaps are subject to the throttle.
    address public immutable arbiterSafe;

    /// @notice Minimum seconds between two consecutive arbiter swaps on a pool.
    uint32 public immutable cooldownSeconds;

    /// @notice Rolling window for the notional cap, in seconds.
    uint32 public immutable windowSeconds;

    /// @notice Maximum notional (in input-token base units) per window.
    uint128 public immutable maxNotionalPerWindow;

    /// @notice Per-pool cooldown bookkeeping.
    mapping(bytes32 => uint64) public lastSwapAt;

    /// @notice Per-pool rolling-window accounting.
    mapping(bytes32 => uint64)  public windowStartedAt;
    mapping(bytes32 => uint128) public windowNotionalUsed;

    error CooldownNotElapsed(uint32 remaining);
    error NotionalCapExceeded(uint128 used, uint128 attempted, uint128 cap);

    event ArbiterSwapAccepted(bytes32 indexed poolId, uint128 notionalAdded, uint128 windowTotal);

    constructor(
        IPoolManager _manager,
        address _arbiterSafe,
        uint32 _cooldownSeconds,
        uint32 _windowSeconds,
        uint128 _maxNotionalPerWindow
    ) BaseHook(_manager) {
        require(_arbiterSafe != address(0), "ArbiterThrottle: zero safe");
        require(_windowSeconds > 0, "ArbiterThrottle: zero window");
        require(_maxNotionalPerWindow > 0, "ArbiterThrottle: zero cap");
        arbiterSafe = _arbiterSafe;
        cooldownSeconds = _cooldownSeconds;
        windowSeconds = _windowSeconds;
        maxNotionalPerWindow = _maxNotionalPerWindow;
    }

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false,
            afterInitialize: false,
            beforeAddLiquidity: false,
            afterAddLiquidity: false,
            beforeRemoveLiquidity: false,
            afterRemoveLiquidity: false,
            beforeSwap: true,
            afterSwap: true,
            beforeDonate: false,
            afterDonate: false,
            beforeSwapReturnDelta: false,
            afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false,
            afterRemoveLiquidityReturnDelta: false
        });
    }

    function _poolId(PoolKey calldata key) internal pure returns (bytes32) {
        return keccak256(abi.encode(key));
    }

    function _beforeSwap(
        address sender,
        PoolKey calldata key,
        IPoolManager.SwapParams calldata params,
        bytes calldata
    ) internal override returns (bytes4, BeforeSwapDelta, uint24) {
        if (sender != arbiterSafe) {
            return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
        }

        bytes32 pid = _poolId(key);
        uint64 nowTs = uint64(block.timestamp);

        // Cooldown check
        uint64 last = lastSwapAt[pid];
        if (last != 0 && nowTs < last + cooldownSeconds) {
            revert CooldownNotElapsed(uint32(last + cooldownSeconds - nowTs));
        }

        // Roll window if expired
        uint64 wStart = windowStartedAt[pid];
        if (wStart == 0 || nowTs >= wStart + windowSeconds) {
            windowStartedAt[pid] = nowTs;
            windowNotionalUsed[pid] = 0;
        }

        // Notional pre-check
        uint128 attempted = uint128(uint256(params.amountSpecified < 0
            ? uint256(-params.amountSpecified)
            : uint256(params.amountSpecified)));
        uint128 used = windowNotionalUsed[pid];
        if (used + attempted > maxNotionalPerWindow) {
            revert NotionalCapExceeded(used, attempted, maxNotionalPerWindow);
        }

        return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }

    function _afterSwap(
        address sender,
        PoolKey calldata key,
        IPoolManager.SwapParams calldata params,
        BalanceDelta,
        bytes calldata
    ) internal override returns (bytes4, int128) {
        if (sender != arbiterSafe) {
            return (BaseHook.afterSwap.selector, 0);
        }

        bytes32 pid = _poolId(key);
        uint128 notional = uint128(uint256(params.amountSpecified < 0
            ? uint256(-params.amountSpecified)
            : uint256(params.amountSpecified)));

        windowNotionalUsed[pid] += notional;
        lastSwapAt[pid] = uint64(block.timestamp);

        emit ArbiterSwapAccepted(pid, notional, windowNotionalUsed[pid]);
        return (BaseHook.afterSwap.selector, 0);
    }
}
