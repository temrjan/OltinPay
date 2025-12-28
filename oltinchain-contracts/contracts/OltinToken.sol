// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title OltinToken
 * @dev Gold-backed ERC20 token for OltinChain platform
 * 1 OLTIN = 1 gram of physical gold
 * 
 * Features:
 * - Role-based access control (MINTER, BURNER, PAUSER)
 * - Pausable transfers for emergency
 * - Event logging with orderId for audit trail
 */
contract OltinToken is ERC20, ERC20Burnable, AccessControl, Pausable {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    /// @notice Emitted when tokens are minted (user buys gold)
    event Minted(
        address indexed to,
        uint256 amount,
        string orderId,
        uint256 timestamp
    );

    /// @notice Emitted when tokens are burned (user sells gold)
    event Burned(
        address indexed from,
        uint256 amount,
        string orderId,
        uint256 timestamp
    );

    /**
     * @dev Constructor grants all roles to deployer
     */
    constructor() ERC20("Oltin Gold Token", "OLTIN") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(BURNER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
    }

    /**
     * @notice Mint new tokens when user purchases gold
     * @param to Recipient address
     * @param amount Amount in wei (18 decimals)
     * @param orderId Platform order ID for audit trail
     */
    function mint(
        address to,
        uint256 amount,
        string calldata orderId
    ) external onlyRole(MINTER_ROLE) whenNotPaused {
        require(to != address(0), "OltinToken: mint to zero address");
        require(amount > 0, "OltinToken: amount must be positive");
        require(bytes(orderId).length > 0, "OltinToken: orderId required");

        _mint(to, amount);
        emit Minted(to, amount, orderId, block.timestamp);
    }

    /**
     * @notice Burn tokens when user sells gold
     * @param from Token holder address
     * @param amount Amount in wei (18 decimals)
     * @param orderId Platform order ID for audit trail
     */
    function burn(
        address from,
        uint256 amount,
        string calldata orderId
    ) external onlyRole(BURNER_ROLE) whenNotPaused {
        require(from != address(0), "OltinToken: burn from zero address");
        require(amount > 0, "OltinToken: amount must be positive");
        require(bytes(orderId).length > 0, "OltinToken: orderId required");
        require(balanceOf(from) >= amount, "OltinToken: insufficient balance");

        _burn(from, amount);
        emit Burned(from, amount, orderId, block.timestamp);
    }

    /**
     * @notice Pause all token transfers (emergency)
     */
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause token transfers
     */
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /**
     * @dev Override to add pause check to transfers
     */
    function _update(
        address from,
        address to,
        uint256 value
    ) internal override whenNotPaused {
        super._update(from, to, value);
    }

    /**
     * @notice Returns 18 decimals for fractional gram support
     * @dev 0.000000000000000001 OLTIN = 1 attogram
     */
    function decimals() public pure override returns (uint8) {
        return 18;
    }
}
