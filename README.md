
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
import asyncio
import time

async def swap():
    start_time = time.time()

    keypair = Keypair.from_base58_string("YOUR_SECRET_KEY")  # Replace with your base58 private key
    
    solana_tracker = SolanaTracker(keypair, "https://rpc.solanatracker.io/public?advancedTx=true") # Your RPC Here
    
    swap_response = await solana_tracker.get_swap_instructions(
        "So11111111111111111111111111111111111111112",  # From Token
        "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # To Token
        0.005,  # Amount to swap
        30,  # Slippage
        str(keypair.pubkey()),  # Payer public key
        0.005,  # Priority fee (Recommended while network is congested)
        True,  # Force legacy transaction for Jupiter
    )

    # fix processed commitment
    
    # Define custom options
    custom_options = {
        "send_options": {"skip_preflight": True, "max_retries": 5},
        "confirmation_retries": 50,
        "confirmation_retry_timeout": 1000,
        "last_valid_block_height_buffer": 200,
        "commitment": "processed",
        "resend_interval": 1500,
        "confirmation_check_interval": 100,
        "skip_confirmation_check": False,
    }
    
    try:
        send_time = time.time()
        txid = await solana_tracker.perform_swap(swap_response, options=custom_options)
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print("Transaction ID:", txid)
        print("Transaction URL:", f"https://solscan.io/tx/{txid}")
        print(f"Swap completed in {elapsed_time:.2f} seconds")
        print(f"Transaction finished in {end_time - send_time:.2f} seconds")
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print("Swap failed:", str(e))
        print(f"Time elapsed before failure: {elapsed_time:.2f} seconds")
        # Add retries or additional error handling as needed

if __name__ == "__main__":
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