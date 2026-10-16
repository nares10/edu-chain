# edu-chain

A tiny, readable blockchain in pure Python, built for teaching. No dependencies, one core file you can read top to bottom.

## What it demonstrates

| Concept | Where |
|---|---|
| Blocks & SHA-256 hashing, chained by `previous_hash` | `Block`, `compute_hash()` |
| Transactions & balances (computed by replaying the ledger) | `Transaction`, `get_balance()`, `add_transaction()` |
| Mining with Proof of Work (leading-zero difficulty) | `proof_of_work()`, `mine()` |
| Chain validation: links, tampering, PoW, overspending, rewards | `validate_chain()` |
| Consensus: longest valid chain wins | `Node.resolve_conflicts()` |

## Run it

```bash
python demo.py               # guided walkthrough of every concept
python -m unittest -v        # 10 tests
```

Requires Python 3.9+. No packages to install.

## Sample output

```
4. Tampering is detected
Changed Alice->Bob from 20 to 2000 coins.
Valid? (False, 'Block #2 was tampered with (hash mismatch).')

5. Consensus: longest valid chain wins
Before: Node A has 3 blocks, Node B has 2 blocks  (they disagree)
Node B replaced its chain? True
Same ledger? True
```

## Files

- `edu_chain.py` — the blockchain (Transaction, Block, Blockchain, Node)
- `demo.py` — step-by-step tour with printed explanations
- `test_edu_chain.py` — unit tests, including tampering and forged-chain attacks

## Deliberately left out

Digital signatures, real networking and Merkle trees are omitted to keep the core ideas visible. Each is a natural next lesson.
