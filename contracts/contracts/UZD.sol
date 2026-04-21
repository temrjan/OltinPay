// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title UZD - Uzbek Sum Digital
 * @notice DEMO stablecoin pegged 1:1 to UZS. No real fiat backing.
 * @dev ERC20 with admin mint/burn. Designed for the OltinPay regulatory pilot demo.
 *      Production deployment requires fiat reserve and НАПП stablecoin licence.
 */
contract UZD is ERC20, ERC20Burnable, AccessControl, Pausable {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    event Minted(address indexed to, uint256 amount, uint256 timestamp);
    event AdminBurned(address indexed from, uint256 amount, uint256 timestamp);

    constructor() ERC20("Uzbek Sum Digital", "UZD") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(BURNER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
    }

    /// @notice Mint UZD to address (e.g. for welcome bonus or fiat deposit)
    function mint(address to, uint256 amount)
        external
        onlyRole(MINTER_ROLE)
        whenNotPaused
    {
        require(to != address(0), "Zero address");
        require(amount > 0, "Zero amount");
        _mint(to, amount);
        emit Minted(to, amount, block.timestamp);
    }

    /// @notice Admin burn from any holder (for fiat redemption)
    function adminBurn(address from, uint256 amount)
        external
        onlyRole(BURNER_ROLE)
        whenNotPaused
    {
        require(from != address(0), "Zero address");
        require(amount > 0, "Zero amount");
        _burn(from, amount);
        emit AdminBurned(from, amount, block.timestamp);
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    function _update(address from, address to, uint256 value)
        internal
        override
        whenNotPaused
    {
        super._update(from, to, value);
    }

    function decimals() public pure override returns (uint8) {
        return 18;
    }
}
