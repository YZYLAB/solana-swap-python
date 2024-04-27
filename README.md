
# Solana Swap by Solana Tracker

Easiest way to add Solana based swaps to your project.
Uses the Solana Swap api from [https://docs.solanatracker.io](https://docs.solanatracker.io)

## Now supporting
- Raydium
- Pump.fun
- Jupiter

## Installation

```bash
git clone https://github.com/YZYLAB/solana-swap-python.git
```

## Demo

Swap API is used live on:
https://www.solanatracker.io

*Add your site here*


## Example Usage

```python
from solders.keypair import Keypair
from solanatracker import SolanaTracker

async def swap():
    keypair = Keypair.from_base58_string("YOUR_SECRET_KEY_HERE")

    solana_tracker = SolanaTracker(keypair, "https://api.solanatracker.io/rpc")

    swap_response = await solana_tracker.get_swap_instructions(
        "So11111111111111111111111111111111111111112",  # From Token
        "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # To Token
        0.0005,  # Amount to swap
        30,  # Slippage
        str(keypair.pubkey()),  # Payer public key
        0.00000005,  # Priority fee (Recommended while network is congested)
        True,  # Force legacy transaction for Jupiter
    )

    txid = await solana_tracker.perform_swap(swap_response)

    # Returns txid when the swap is successful or raises an exception if the swap fails
    print("Transaction ID:", txid)
    print("Transaction URL:", f"https://explorer.solana.com/tx/{txid}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(swap())
```


## FAQ

#### Why should I use this API?

We retrieve all raydium tokens the second they are available, so you can perform fast snipes.
We also provide our own hosted Jupiter Swap API with no rate limits and faster market updates.

#### Is there a fee for using this API?

We charge a 0.9% fee on each successful transaction
.
Using this for a public bot or site with a high processing volume? 
Contact us via Discord or email (solanatracker@yzylab.com) and get the fee reduced to 0.1% (only if accepted.)