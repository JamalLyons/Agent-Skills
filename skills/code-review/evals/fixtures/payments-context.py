"""Unchanged code used by both base and proposed withdraw implementations."""
import asyncio


class Store:
    def __init__(self):
        self.balances = {"alice": 100}
        self.lock = asyncio.Lock()

    async def debit_if_sufficient(self, account_id, amount):
        async with self.lock:
            if self.balances[account_id] < amount:
                return False
            self.balances[account_id] -= amount
            return True

    async def get_balance(self, account_id):
        balance = self.balances[account_id]
        await asyncio.sleep(0)
        return balance

    async def set_balance(self, account_id, balance):
        await asyncio.sleep(0)
        self.balances[account_id] = balance


# Independent HTTP requests share the store and may call withdraw concurrently.
# Input validation before withdraw guarantees amount > 0 and account_id exists.
