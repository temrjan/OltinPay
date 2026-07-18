// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

interface IExchangeAttack {
    function buy(uint256 uzdInWei, uint256 minOltinOut)
        external
        returns (uint256);

    function sell(uint256 oltinInWei, uint256 minUzdOut)
        external
        returns (uint256);
}

/**
 * @title MaliciousReentrant
 * @notice TEST-ONLY ERC20 that stands in for UZD and attempts to re-enter the
 *         {Exchange} from inside its own transfer hook:
 *           - during `buy`  the Exchange calls `transferFrom` (pull) -> re-enter buy
 *           - during `sell` the Exchange calls `transfer` (payout)   -> re-enter sell
 *         Each re-entry must be rejected by the Exchange's {ReentrancyGuard},
 *         reverting the whole outer call.
 */
contract MaliciousReentrant is ERC20 {
    IExchangeAttack public exchange;
    bool public attackBuy;
    bool public attackSell;

    constructor() ERC20("Malicious UZD", "MUZD") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function setExchange(address e) external {
        exchange = IExchangeAttack(e);
    }

    function setAttackBuy(bool v) external {
        attackBuy = v;
    }

    function setAttackSell(bool v) external {
        attackSell = v;
    }

    function _update(address from, address to, uint256 value)
        internal
        override
    {
        super._update(from, to, value);
        // One-shot flags: even if the guard were absent, we would not recurse
        // forever. With the guard present, the re-entrant call reverts here and
        // takes the whole outer buy()/sell() down with it.
        if (attackBuy) {
            attackBuy = false;
            exchange.buy(1, 1);
        } else if (attackSell) {
            attackSell = false;
            exchange.sell(1, 0);
        }
    }
}
