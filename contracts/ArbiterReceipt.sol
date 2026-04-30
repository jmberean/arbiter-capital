// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

/// @title ArbiterReceipt — Soulbound Decision Receipt (ERC-721 SBT)
/// @notice Minted by the Execution Node to the Safe treasury on every successful trade.
///         tokenURI points to the 0G receipt tx hash for full on-chain auditability.
///         Non-transferable: tokens are bound to the Safe address forever.
contract ArbiterReceipt is ERC721 {
    address public immutable safeTreasury;
    address public immutable executor; // execution node EOA — the only minter

    mapping(uint256 => string) private _tokenURIs;

    error OnlyExecutor();
    error SoulboundNonTransferable();

    constructor(address _safe, address _executor)
        ERC721("Arbiter Decision Receipt", "ARDR")
    {
        safeTreasury = _safe;
        executor = _executor;
    }

    /// @notice Mint a receipt for a settled decision.
    /// @param receiptHash keccak256 of the DecisionReceipt JSON (used as token id).
    /// @param zeroGUri    "0g://0x<tx_hash>" pointing to the full receipt on 0G.
    function mintReceipt(bytes32 receiptHash, string calldata zeroGUri)
        external
        returns (uint256 tokenId)
    {
        if (msg.sender != executor) revert OnlyExecutor();
        tokenId = uint256(receiptHash);
        _safeMint(safeTreasury, tokenId);
        _tokenURIs[tokenId] = zeroGUri;
    }

    function tokenURI(uint256 tokenId)
        public
        view
        override
        returns (string memory)
    {
        return _tokenURIs[tokenId];
    }

    /// @dev SBT enforcement: block all transfers except mint (from == 0) and burn (to == 0).
    function _update(address to, uint256 tokenId, address auth)
        internal
        override
        returns (address)
    {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) revert SoulboundNonTransferable();
        return super._update(to, tokenId, auth);
    }
}
