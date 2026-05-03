// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {IHooks} from "v4-core/interfaces/IHooks.sol";
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
///         Hook address bits must encode beforeSwap + afterSwap (0x00C0).
contract ArbiterThrottleHook is IHooks {
    IPoolManager public immutable poolManager;

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
    error NotPoolManager();

    event ArbiterSwapAccepted(bytes32 indexed poolId, uint128 notionalAdded, uint128 windowTotal);

    modifier onlyPoolManager() {
        if (msg.sender != address(poolManager)) revert NotPoolManager();
        _;
    }

    constructor(
        IPoolManager _manager,
        address _arbiterSafe,
        uint32 _cooldownSeconds,
        uint32 _windowSeconds,
        uint128 _maxNotionalPerWindow
    ) {
        require(_arbiterSafe != address(0), "ArbiterThrottle: zero safe");
        require(_windowSeconds > 0, "ArbiterThrottle: zero window");
        require(_maxNotionalPerWindow > 0, "ArbiterThrottle: zero cap");
        poolManager = _manager;
        arbiterSafe = _arbiterSafe;
        cooldownSeconds = _cooldownSeconds;
        windowSeconds = _windowSeconds;
        maxNotionalPerWindow = _maxNotionalPerWindow;
    }

    /// @notice Returns the hook permission flags for deployment address mining.
    function getHookPermissions() public pure returns (Hooks.Permissions memory) {
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

    // ── Active hooks ──────────────────────────────────────────────────────────

    function beforeSwap(
        address sender,
        PoolKey calldata key,
        IPoolManager.SwapParams calldata params,
        bytes calldata
    ) external override onlyPoolManager returns (bytes4, BeforeSwapDelta, uint24) {
        if (sender != arbiterSafe) {
            return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
        }

        bytes32 pid = _poolId(key);
        uint64 nowTs = uint64(block.timestamp);

        uint64 last = lastSwapAt[pid];
        if (last != 0 && nowTs < last + cooldownSeconds) {
            revert CooldownNotElapsed(uint32(last + cooldownSeconds - nowTs));
        }

        uint64 wStart = windowStartedAt[pid];
        if (wStart == 0 || nowTs >= wStart + windowSeconds) {
            windowStartedAt[pid] = nowTs;
            windowNotionalUsed[pid] = 0;
        }

        uint128 attempted = uint128(uint256(params.amountSpecified < 0
            ? uint256(-params.amountSpecified)
            : uint256(params.amountSpecified)));
        uint128 used = windowNotionalUsed[pid];
        if (used + attempted > maxNotionalPerWindow) {
            revert NotionalCapExceeded(used, attempted, maxNotionalPerWindow);
        }

        return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }

    function afterSwap(
        address sender,
        PoolKey calldata key,
        IPoolManager.SwapParams calldata params,
        BalanceDelta,
        bytes calldata
    ) external override onlyPoolManager returns (bytes4, int128) {
        if (sender != arbiterSafe) {
            return (IHooks.afterSwap.selector, 0);
        }

        bytes32 pid = _poolId(key);
        uint128 notional = uint128(uint256(params.amountSpecified < 0
            ? uint256(-params.amountSpecified)
            : uint256(params.amountSpecified)));

        windowNotionalUsed[pid] += notional;
        lastSwapAt[pid] = uint64(block.timestamp);

        emit ArbiterSwapAccepted(pid, notional, windowNotionalUsed[pid]);
        return (IHooks.afterSwap.selector, 0);
    }

    // ── Stub hooks (not enabled, but required by IHooks) ─────────────────────

    function beforeInitialize(address, PoolKey calldata, uint160) external pure override returns (bytes4) {
        return IHooks.beforeInitialize.selector;
    }

    function afterInitialize(address, PoolKey calldata, uint160, int24) external pure override returns (bytes4) {
        return IHooks.afterInitialize.selector;
    }

    function beforeAddLiquidity(address, PoolKey calldata, IPoolManager.ModifyLiquidityParams calldata, bytes calldata)
        external pure override returns (bytes4) {
        return IHooks.beforeAddLiquidity.selector;
    }

    function afterAddLiquidity(
        address, PoolKey calldata, IPoolManager.ModifyLiquidityParams calldata,
        BalanceDelta, BalanceDelta, bytes calldata
    ) external pure override returns (bytes4, BalanceDelta) {
        return (IHooks.afterAddLiquidity.selector, BalanceDelta.wrap(0));
    }

    function beforeRemoveLiquidity(address, PoolKey calldata, IPoolManager.ModifyLiquidityParams calldata, bytes calldata)
        external pure override returns (bytes4) {
        return IHooks.beforeRemoveLiquidity.selector;
    }

    function afterRemoveLiquidity(
        address, PoolKey calldata, IPoolManager.ModifyLiquidityParams calldata,
        BalanceDelta, BalanceDelta, bytes calldata
    ) external pure override returns (bytes4, BalanceDelta) {
        return (IHooks.afterRemoveLiquidity.selector, BalanceDelta.wrap(0));
    }

    function beforeDonate(address, PoolKey calldata, uint256, uint256, bytes calldata)
        external pure override returns (bytes4) {
        return IHooks.beforeDonate.selector;
    }

    function afterDonate(address, PoolKey calldata, uint256, uint256, bytes calldata)
        external pure override returns (bytes4) {
        return IHooks.afterDonate.selector;
    }
}
