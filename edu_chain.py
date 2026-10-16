"""
edu_chain.py — a tiny, readable blockchain for learning.

Every core idea lives in this one file and is meant to be read top to bottom:

    1. Transaction  – a transfer of value between two participants
    2. Block        – a bundle of transactions, linked to the previous block by its hash
    3. Blockchain   – the ledger: balances, Proof of Work mining, chain validation
    4. Node         – a participant in a network that resolves conflicts (consensus)

Nothing here is production-grade (no signatures, no networking). The goal is clarity.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #

NETWORK = "NETWORK"      # Special "sender" that creates new coins as mining rewards
MINING_REWARD = 50       # Coins paid to whoever mines a block
DEFAULT_DIFFICULTY = 4   # Number of leading zeros a valid block hash must have


# --------------------------------------------------------------------------- #
# 1. Transaction
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Transaction:
    """A transfer of `amount` coins from `sender` to `recipient`.

    `frozen=True` makes a transaction immutable once created, which mirrors
    how a transaction can't be changed after it is recorded in a block.
    """

    sender: str
    recipient: str
    amount: int

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# 2. Block
# --------------------------------------------------------------------------- #

@dataclass
class Block:
    """A block stores transactions plus the hash of the block before it.

    That `previous_hash` field is what "chains" blocks together: change any
    old block and its hash changes, which breaks the link to every block after it.
    """

    index: int
    transactions: list[Transaction]
    previous_hash: str
    timestamp: float = field(default_factory=time.time)
    nonce: int = 0          # The number miners change while searching for a valid hash
    hash: str = ""

    def compute_hash(self) -> str:
        """Return the SHA-256 fingerprint of this block's contents.

        The data is turned into JSON with sorted keys so the same block
        always produces exactly the same hash.
        """
        block_data = {
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }
        encoded = json.dumps(block_data, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    def __str__(self) -> str:
        txs = ", ".join(f"{t.sender}->{t.recipient}:{t.amount}" for t in self.transactions)
        return (f"Block #{self.index} | nonce={self.nonce} | "
                f"hash={self.hash[:16]}... | prev={self.previous_hash[:16]}... | [{txs}]")


def create_genesis_block() -> Block:
    """The first block. Every node creates the identical genesis block,
    so all nodes share the same starting point."""
    genesis = Block(index=0, transactions=[], previous_hash="0" * 64, timestamp=0)
    genesis.hash = genesis.compute_hash()
    return genesis


# --------------------------------------------------------------------------- #
# 3. Blockchain
# --------------------------------------------------------------------------- #

class Blockchain:
    """The ledger: a list of blocks plus transactions waiting to be mined."""

    def __init__(self, difficulty: int = DEFAULT_DIFFICULTY):
        self.difficulty = difficulty
        self.chain: list[Block] = [create_genesis_block()]
        self.pending: list[Transaction] = []   # Transactions not yet in a block

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    # ---- Balances ---------------------------------------------------------

    def get_balance(self, address: str, include_pending: bool = False) -> int:
        """Balance = everything received minus everything sent.

        There are no stored account balances in a blockchain; we
        calculate them by replaying all transactions.
        """
        transactions = [tx for block in self.chain for tx in block.transactions]
        if include_pending:
            transactions += self.pending

        balance = 0
        for tx in transactions:
            if tx.recipient == address:
                balance += tx.amount
            if tx.sender == address:
                balance -= tx.amount
        return balance

    def add_transaction(self, sender: str, recipient: str, amount: int) -> Transaction:
        """Queue a transfer, after checking the sender can afford it."""
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        if sender == NETWORK:
            raise ValueError("Only miners receive coins from the NETWORK.")

        # Include pending transfers so nobody can spend the same coins twice
        available = self.get_balance(sender, include_pending=True)
        if available < amount:
            raise ValueError(f"{sender} has {available} coins, cannot send {amount}.")

        tx = Transaction(sender, recipient, amount)
        self.pending.append(tx)
        return tx

    # ---- Mining (Proof of Work) -----------------------------------------

    def proof_of_work(self, block: Block) -> str:
        """Try nonce = 0, 1, 2, ... until the hash starts with enough zeros.

        Finding such a hash takes many attempts (it is "work"),
        but anyone can check it with a single hash. That asymmetry is
        what makes rewriting history expensive.
        """
        target = "0" * self.difficulty
        block.nonce = 0
        block_hash = block.compute_hash()
        while not block_hash.startswith(target):
            block.nonce += 1
            block_hash = block.compute_hash()
        return block_hash

    def mine(self, miner: str) -> Block:
        """Bundle pending transactions into a new block and secure it with PoW.

        The miner is paid with a reward transaction from the NETWORK,
        which is how new coins enter the system.
        """
        reward = Transaction(NETWORK, miner, MINING_REWARD)
        block = Block(
            index=len(self.chain),
            transactions=self.pending + [reward],
            previous_hash=self.last_block.hash,
        )
        block.hash = self.proof_of_work(block)
        self.chain.append(block)
        self.pending = []
        return block

    # ---- Validation ---------------------------------------------------------

    @staticmethod
    def validate_chain(chain: list[Block], difficulty: int) -> tuple[bool, str]:
        """Check a whole chain from scratch. Returns (is_valid, reason).

        Checks performed for every block:
          1. It points to the hash of the previous block   (chaining)
          2. Its stored hash matches its contents          (tamper detection)
          3. Its hash meets the difficulty target          (Proof of Work)
          4. Every sender could afford what they sent      (no overspending)
          5. Exactly one correct mining reward, at the end (no free coins)
        """
        if not chain or chain[0].hash != create_genesis_block().hash:
            return False, "Genesis block does not match."

        target = "0" * difficulty
        balances: dict[str, int] = {}

        for i in range(1, len(chain)):
            block, previous = chain[i], chain[i - 1]

            if block.index != i:
                return False, f"Block #{i} has the wrong index."
            if block.previous_hash != previous.hash:
                return False, f"Block #{i} is not linked to block #{i - 1}."
            if block.hash != block.compute_hash():
                return False, f"Block #{i} was tampered with (hash mismatch)."
            if not block.hash.startswith(target):
                return False, f"Block #{i} has no valid Proof of Work."
            if not block.transactions:
                return False, f"Block #{i} has no mining reward."

            *transfers, reward = block.transactions
            if reward.sender != NETWORK or reward.amount != MINING_REWARD:
                return False, f"Block #{i} has an invalid mining reward."

            for tx in transfers:
                if tx.sender == NETWORK:
                    return False, f"Block #{i} creates coins outside the reward."
                if tx.amount <= 0:
                    return False, f"Block #{i} has a non-positive transfer."
                if balances.get(tx.sender, 0) < tx.amount:
                    return False, f"Block #{i}: {tx.sender} spends coins they don't have."
                balances[tx.sender] -= tx.amount
                balances[tx.recipient] = balances.get(tx.recipient, 0) + tx.amount

            balances[reward.recipient] = balances.get(reward.recipient, 0) + reward.amount

        return True, "Chain is valid."

    def is_valid(self) -> bool:
        return self.validate_chain(self.chain, self.difficulty)[0]


# --------------------------------------------------------------------------- #
# 4. Node and consensus
# --------------------------------------------------------------------------- #

class Node:
    """A participant that keeps its own copy of the blockchain.

    Nodes can disagree (for example, two miners find blocks at the same time).
    They settle it with the "longest valid chain wins" rule: the valid chain
    with the most blocks contains the most Proof of Work, so everyone adopts it.
    """

    def __init__(self, name: str, difficulty: int = DEFAULT_DIFFICULTY):
        self.name = name
        self.blockchain = Blockchain(difficulty)
        self.peers: list[Node] = []

    def connect(self, other: Node) -> None:
        """Connect two nodes to each other."""
        if other not in self.peers:
            self.peers.append(other)
            other.peers.append(self)

    def resolve_conflicts(self) -> bool:
        """Replace our chain with a peer's chain if it is longer and valid.

        Returns True if our chain was replaced.
        """
        best_chain = self.blockchain.chain
        difficulty = self.blockchain.difficulty

        for peer in self.peers:
            candidate = peer.blockchain.chain
            if len(candidate) > len(best_chain):
                valid, _ = Blockchain.validate_chain(candidate, difficulty)
                if valid:
                    best_chain = candidate

        if best_chain is self.blockchain.chain:
            return False

        # Deep copy so each node owns its data, just like separate computers
        self.blockchain.chain = copy.deepcopy(best_chain)
        # Pending transactions may no longer be valid on the new chain;
        # for simplicity we drop them (a real node would re-check each one).
        self.blockchain.pending = []
        return True
