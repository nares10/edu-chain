"""
demo.py — a guided tour of edu_chain.py.  Run:  python demo.py
"""

import time

from edu_chain import Blockchain, Node, Transaction


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# --------------------------------------------------------------------------- #
section("1. Mining with Proof of Work")
chain = Blockchain(difficulty=4)

start = time.time()
block = chain.mine("Alice")
print(f"Alice mined a block in {time.time() - start:.2f}s after trying {block.nonce + 1} nonces.")
print(block)
print("Alice's balance:", chain.get_balance("Alice"))

# --------------------------------------------------------------------------- #
section("2. Transactions and balances")
chain.add_transaction("Alice", "Bob", 20)
chain.add_transaction("Alice", "Carol", 10)
chain.mine("Bob")  # Bob mines the block holding these transfers
for person in ("Alice", "Bob", "Carol"):
    print(f"{person:5}: {chain.get_balance(person)}")

try:
    chain.add_transaction("Carol", "Bob", 999)
except ValueError as error:
    print("Rejected:", error)

# --------------------------------------------------------------------------- #
section("3. The chain and validation")
for b in chain.chain:
    print(b)
print("\nValid?", Blockchain.validate_chain(chain.chain, chain.difficulty))

# --------------------------------------------------------------------------- #
section("4. Tampering is detected")
original = chain.chain[2].transactions[0]
chain.chain[2].transactions[0] = Transaction("Alice", "Bob", 2000)  # rewrite history
print("Changed Alice->Bob from 20 to 2000 coins.")
print("Valid?", Blockchain.validate_chain(chain.chain, chain.difficulty))
chain.chain[2].transactions[0] = original  # put it back

# --------------------------------------------------------------------------- #
section("5. Consensus: longest valid chain wins")
node_a = Node("Node A")
node_b = Node("Node B")
node_a.connect(node_b)

node_a.blockchain.mine("Alice")
node_a.blockchain.mine("Alice")
node_b.blockchain.mine("Bob")
print(f"Before: Node A has {len(node_a.blockchain.chain)} blocks, "
      f"Node B has {len(node_b.blockchain.chain)} blocks  (they disagree)")

replaced = node_b.resolve_conflicts()
print(f"Node B replaced its chain? {replaced}")
print(f"After:  Node A has {len(node_a.blockchain.chain)} blocks, "
      f"Node B has {len(node_b.blockchain.chain)} blocks")
print("Same ledger?", node_a.blockchain.last_block.hash == node_b.blockchain.last_block.hash)
print("Bob's balance on Node B now:", node_b.blockchain.get_balance("Bob"),
      "(his block lost the race)")
