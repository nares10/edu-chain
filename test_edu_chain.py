"""Unit tests.  Run:  python -m unittest -v"""

import unittest

from edu_chain import MINING_REWARD, Blockchain, Node, Transaction

DIFFICULTY = 2  # Low difficulty keeps the tests fast


class TestBlockchain(unittest.TestCase):
    def setUp(self):
        self.chain = Blockchain(DIFFICULTY)

    def test_genesis_chain_is_valid(self):
        self.assertTrue(self.chain.is_valid())

    def test_mining_meets_difficulty_and_pays_reward(self):
        block = self.chain.mine("Alice")
        self.assertTrue(block.hash.startswith("0" * DIFFICULTY))
        self.assertEqual(self.chain.get_balance("Alice"), MINING_REWARD)

    def test_blocks_are_linked(self):
        self.chain.mine("Alice")
        self.chain.mine("Alice")
        for prev, block in zip(self.chain.chain, self.chain.chain[1:]):
            self.assertEqual(block.previous_hash, prev.hash)

    def test_transfer_updates_balances(self):
        self.chain.mine("Alice")
        self.chain.add_transaction("Alice", "Bob", 30)
        self.chain.mine("Carol")
        self.assertEqual(self.chain.get_balance("Alice"), MINING_REWARD - 30)
        self.assertEqual(self.chain.get_balance("Bob"), 30)

    def test_overspending_is_rejected(self):
        with self.assertRaises(ValueError):
            self.chain.add_transaction("Bob", "Alice", 1)

    def test_double_spend_in_pending_is_rejected(self):
        self.chain.mine("Alice")
        self.chain.add_transaction("Alice", "Bob", 40)
        with self.assertRaises(ValueError):
            self.chain.add_transaction("Alice", "Carol", 40)

    def test_tampering_is_detected(self):
        self.chain.mine("Alice")
        self.chain.chain[1].transactions[0] = Transaction("NETWORK", "Mallory", 1000)
        valid, reason = Blockchain.validate_chain(self.chain.chain, DIFFICULTY)
        self.assertFalse(valid)
        self.assertIn("tampered", reason)

    def test_remined_forgery_still_fails_balance_check(self):
        # Even if an attacker redoes the Proof of Work, overspending is caught
        self.chain.mine("Alice")
        block = self.chain.chain[1]
        block.transactions = [Transaction("Bob", "Mallory", 500)] + block.transactions
        block.hash = self.chain.proof_of_work(block)
        valid, reason = Blockchain.validate_chain(self.chain.chain, DIFFICULTY)
        self.assertFalse(valid)
        self.assertIn("spends coins", reason)


class TestConsensus(unittest.TestCase):
    def test_longer_valid_chain_wins(self):
        a, b = Node("A", DIFFICULTY), Node("B", DIFFICULTY)
        a.connect(b)
        a.blockchain.mine("Alice")
        a.blockchain.mine("Alice")
        b.blockchain.mine("Bob")
        self.assertTrue(b.resolve_conflicts())
        self.assertEqual(b.blockchain.last_block.hash, a.blockchain.last_block.hash)

    def test_longer_invalid_chain_is_ignored(self):
        honest, cheater = Node("Honest", DIFFICULTY), Node("Cheater", DIFFICULTY)
        honest.connect(cheater)
        honest.blockchain.mine("Alice")
        for _ in range(3):
            cheater.blockchain.mine("Mallory")
        cheater.blockchain.chain[2].transactions[0] = Transaction("NETWORK", "Mallory", 10**6)
        self.assertFalse(honest.resolve_conflicts())
        self.assertEqual(len(honest.blockchain.chain), 2)


if __name__ == "__main__":
    unittest.main()
