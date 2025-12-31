"""Trading bots."""

from bots.base import BaseBot, Order
from bots.market_maker import MarketMakerBot
from bots.arbitrageur import ArbitrageurBot
from bots.momentum import MomentumBot
from bots.whale import WhaleBot

__all__ = [
    "BaseBot",
    "Order",
    "MarketMakerBot",
    "ArbitrageurBot",
    "MomentumBot",
    "WhaleBot",
]
