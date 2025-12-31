// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IPaymaster, ExecutionResult, PAYMASTER_VALIDATION_SUCCESS_MAGIC} from "@matterlabs/zksync-contracts/contracts/system-contracts/interfaces/IPaymaster.sol";
import {IPaymasterFlow} from "@matterlabs/zksync-contracts/contracts/system-contracts/interfaces/IPaymasterFlow.sol";
import {Transaction} from "@matterlabs/zksync-contracts/contracts/system-contracts/libraries/TransactionHelper.sol";
import {BOOTLOADER_FORMAL_ADDRESS} from "@matterlabs/zksync-contracts/contracts/system-contracts/Constants.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title OltinPaymaster
 * @notice Paymaster that accepts OLTIN tokens as fee payment
 * @dev Users pay transfer fees in OLTIN, Paymaster covers ETH gas
 * 
 * Flow:
 * 1. User approves Paymaster to spend OLTIN
 * 2. User sends tx with paymasterParams
 * 3. Paymaster takes OLTIN fee, pays ETH gas
 * 4. User gets gasless transaction
 */
contract OltinPaymaster is IPaymaster, Ownable {

    IERC20 public immutable oltinToken;
    
    /// @notice Fee in basis points (100 = 1%, 50 = 0.5%)
    uint256 public feeBasisPoints = 50;
    
    /// @notice Minimum fee in OLTIN (wei, 18 decimals)
    uint256 public minFeeWei = 0.0001 ether; // 0.0001 gram
    
    /// @notice Accumulated fees
    uint256 public totalFeesCollected;
    
    event FeePaid(
        address indexed user,
        uint256 oltinFee,
        bytes32 indexed txHash
    );
    event FeesWithdrawn(address indexed to, uint256 amount);
    event FeeConfigUpdated(uint256 basisPoints, uint256 minFee);

    modifier onlyBootloader() {
        require(
            msg.sender == BOOTLOADER_FORMAL_ADDRESS,
            "Paymaster: not bootloader"
        );
        _;
    }

    constructor(address _oltinToken) Ownable(msg.sender) {
        require(_oltinToken != address(0), "Invalid token");
        oltinToken = IERC20(_oltinToken);
    }

    /**
     * @notice Validate transaction and collect OLTIN fee
     */
    function validateAndPayForPaymasterTransaction(
        bytes32,
        bytes32,
        Transaction calldata _transaction
    )
        external
        payable
        onlyBootloader
        returns (bytes4 magic, bytes memory context)
    {
        magic = PAYMASTER_VALIDATION_SUCCESS_MAGIC;
        
        // Decode paymaster input to get approval-based flow params
        require(
            _transaction.paymasterInput.length >= 4,
            "Paymaster: invalid input"
        );
        
        bytes4 paymasterInputSelector = bytes4(
            _transaction.paymasterInput[0:4]
        );
        
        require(
            paymasterInputSelector == IPaymasterFlow.approvalBased.selector,
            "Paymaster: unsupported flow"
        );

        // Decode: token, minAllowance, innerInput
        (address token, uint256 minAllowance, ) = abi.decode(
            _transaction.paymasterInput[4:],
            (address, uint256, bytes)
        );
        
        require(token == address(oltinToken), "Paymaster: wrong token");
        
        address user = address(uint160(_transaction.from));
        
        // Calculate fee: basis points of minAllowance or minFee
        uint256 fee = (minAllowance * feeBasisPoints) / 10000;
        if (fee < minFeeWei) {
            fee = minFeeWei;
        }
        
        // Verify allowance
        uint256 allowance = oltinToken.allowance(user, address(this));
        require(allowance >= fee, "Paymaster: allowance too low");
        
        // Collect OLTIN fee
        bool success = oltinToken.transferFrom(user, address(this), fee);
        require(success, "Paymaster: fee transfer failed");
        
        totalFeesCollected += fee;
        
        // Pay ETH to bootloader for gas
        uint256 requiredETH = _transaction.gasLimit * _transaction.maxFeePerGas;
        (bool ethSent, ) = payable(BOOTLOADER_FORMAL_ADDRESS).call{
            value: requiredETH
        }("");
        require(ethSent, "Paymaster: ETH payment failed");
        
        context = abi.encode(user, fee);
    }

    /**
     * @notice Post-transaction callback (refunds, logging)
     */
    function postTransaction(
        bytes calldata _context,
        Transaction calldata,
        bytes32 _txHash,
        bytes32,
        ExecutionResult,
        uint256
    ) external payable override onlyBootloader {
        (address user, uint256 fee) = abi.decode(_context, (address, uint256));
        emit FeePaid(user, fee, _txHash);
    }

    // ============ Admin ============

    function setFeeConfig(
        uint256 _basisPoints, 
        uint256 _minFeeWei
    ) external onlyOwner {
        require(_basisPoints <= 500, "Fee max 5%");
        feeBasisPoints = _basisPoints;
        minFeeWei = _minFeeWei;
        emit FeeConfigUpdated(_basisPoints, _minFeeWei);
    }

    function withdrawFees(address _to) external onlyOwner {
        uint256 amount = totalFeesCollected;
        require(amount > 0, "No fees");
        totalFeesCollected = 0;
        oltinToken.transfer(_to, amount);
        emit FeesWithdrawn(_to, amount);
    }

    function withdrawETH(address payable _to) external onlyOwner {
        (bool success, ) = _to.call{value: address(this).balance}("");
        require(success, "ETH withdraw failed");
    }

    /// @notice Deposit ETH for gas coverage
    receive() external payable {}
}
