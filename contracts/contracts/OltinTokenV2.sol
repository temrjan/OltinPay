// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title OltinToken V2
 * @dev Gold-backed ERC20 with admin transfer (gasless for users)
 */
contract OltinTokenV2 is ERC20, ERC20Burnable, AccessControl, Pausable {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    /// @notice Transfer fee in basis points (50 = 0.5%)
    uint256 public transferFeeBps = 50;
    
    /// @notice Fee collector address
    address public feeCollector;

    event Minted(address indexed to, uint256 amount, string orderId, uint256 timestamp);
    event Burned(address indexed from, uint256 amount, string orderId, uint256 timestamp);
    event AdminTransfer(
        address indexed from, 
        address indexed to, 
        uint256 amount, 
        uint256 fee,
        string transferId
    );
    event FeeConfigUpdated(uint256 feeBps, address collector);

    constructor(address _feeCollector) ERC20("Oltin Gold Token", "OLTIN") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(BURNER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        feeCollector = _feeCollector;
    }

    /**
     * @notice Mint tokens (user buys gold)
     */
    function mint(
        address to,
        uint256 amount,
        string calldata orderId
    ) external onlyRole(MINTER_ROLE) whenNotPaused {
        require(to != address(0), "Zero address");
        require(amount > 0, "Zero amount");
        _mint(to, amount);
        emit Minted(to, amount, orderId, block.timestamp);
    }

    /**
     * @notice Burn tokens (user sells gold)
     */
    function burn(
        address from,
        uint256 amount,
        string calldata orderId
    ) external onlyRole(BURNER_ROLE) whenNotPaused {
        require(from != address(0), "Zero address");
        require(amount > 0, "Zero amount");
        require(balanceOf(from) >= amount, "Insufficient balance");
        _burn(from, amount);
        emit Burned(from, amount, orderId, block.timestamp);
    }

    /**
     * @notice Admin transfer (gasless for users)
     * @dev Only minter can call. Fee deducted from amount.
     * @param from Sender address
     * @param to Recipient address  
     * @param amount Total amount (fee will be deducted)
     * @param transferId Unique transfer ID for audit
     */
    function adminTransfer(
        address from,
        address to,
        uint256 amount,
        string calldata transferId
    ) external onlyRole(MINTER_ROLE) whenNotPaused {
        require(from != address(0) && to != address(0), "Zero address");
        require(amount > 0, "Zero amount");
        require(balanceOf(from) >= amount, "Insufficient balance");
        require(bytes(transferId).length > 0, "Transfer ID required");
        
        // Calculate fee
        uint256 fee = (amount * transferFeeBps) / 10000;
        uint256 netAmount = amount - fee;
        
        // Transfer: from -> to (net amount)
        _update(from, to, netAmount);
        
        // Transfer: from -> feeCollector (fee)
        if (fee > 0 && feeCollector != address(0)) {
            _update(from, feeCollector, fee);
        }
        
        emit AdminTransfer(from, to, netAmount, fee, transferId);
    }

    /**
     * @notice Update fee configuration
     */
    function setFeeConfig(
        uint256 _feeBps,
        address _collector
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_feeBps <= 500, "Fee max 5%");
        transferFeeBps = _feeBps;
        feeCollector = _collector;
        emit FeeConfigUpdated(_feeBps, _collector);
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    function _update(
        address from,
        address to,
        uint256 value
    ) internal override whenNotPaused {
        super._update(from, to, value);
    }

    function decimals() public pure override returns (uint8) {
        return 18;
    }
}
