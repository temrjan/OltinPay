"""Sequential order queue to prevent database deadlocks."""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Dict, Optional
from uuid import UUID, uuid4

from config import config
from models import OrderOperation

logger = logging.getLogger(__name__)


class OrderQueue:
    """
    FIFO queue for order operations.
    Processes operations sequentially to prevent database deadlocks.
    """

    def __init__(self):
        self._queue: asyncio.Queue[OrderOperation] = asyncio.Queue()
        self._results: Dict[UUID, OrderOperation] = {}
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

        # Callbacks for different operation types
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, op_type: str, handler: Callable) -> None:
        """Register a handler for an operation type."""
        self._handlers[op_type] = handler

    async def start(self) -> None:
        """Start the queue processor."""
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Order queue started")

    async def stop(self) -> None:
        """Stop the queue processor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Order queue stopped")

    async def enqueue(
        self,
        op_type: str,
        bot_id: UUID,
        **params,
    ) -> UUID:
        """Add operation to queue and return operation ID."""
        op = OrderOperation(
            id=uuid4(),
            op_type=op_type,
            bot_id=bot_id,
            params=params,
            created_at=datetime.utcnow(),
        )

        await self._queue.put(op)
        logger.debug(f"Enqueued {op_type} for bot {bot_id}: {op.id}")
        return op.id

    async def wait_for_result(
        self, op_id: UUID, timeout: float = 30.0
    ) -> Optional[OrderOperation]:
        """Wait for an operation to complete."""
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            if op_id in self._results:
                return self._results.pop(op_id)
            await asyncio.sleep(0.1)

        logger.warning(f"Timeout waiting for operation {op_id}")
        return None

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Wait for operation with timeout
                try:
                    op = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Process operation
                await self._execute_operation(op)

                # Delay between operations
                await asyncio.sleep(config.queue_delay_ms / 1000)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")

    async def _execute_operation(self, op: OrderOperation) -> None:
        """Execute a single operation."""
        try:
            handler = self._handlers.get(op.op_type)
            if not handler:
                op.error = f"No handler for {op.op_type}"
                logger.error(op.error)
            else:
                result = await handler(op.bot_id, **op.params)
                op.result = result

            op.executed_at = datetime.utcnow()

        except Exception as e:
            op.error = str(e)
            logger.error(f"Operation {op.id} failed: {e}")

        finally:
            self._results[op.id] = op

    @property
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


# Global instance
order_queue = OrderQueue()
