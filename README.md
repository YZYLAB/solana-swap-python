
# Solana Swap by Solana Tracker

Easiest way to add Solana-based swaps to your Python project.

Powered by the [Raptor DEX Aggregator](https://docs.solanatracker.io/raptor/overview) — a high-performance DEX aggregator and Swap API for Solana with multi-hop routing, dynamic slippage, and Yellowstone Jet TPU transaction sending.

## Supported DEXs

Raptor aggregates liquidity across all major Solana DEXs:

### Raydium
- Raydium AMM
- Raydium CLMM
- Raydium CPMM
- Raydium LaunchLab / Launchpad

### Meteora
- Meteora DLMM
- Meteora Dynamic AMM
- Meteora DAMM (Dynamic AMM V2)
- Meteora Curve
- Meteora DBC (Dynamic Bonding Curve)

### Orca
- Whirlpool (legacy)
- Whirlpool V2

### Bonding Curves
- Pump.fun
- Pumpswap
- Heaven (Buy/Sell)
- MoonIt (Buy/Sell)
- Boopfun (Buy/Sell)

### PropAMM
- Humidifi
- Tessera
- Solfi V1/V2

### Other
- FluxBeam
- PancakeSwap V3

## Installation

```bash
git clone https://github.com/YZYLAB/solana-swap-python.git
cd solana-swap-python
pip install -r requirements.txt
```

## Demo

Swap API is used live on:
https://www.solanatracker.io

## Example Usage

```python
from solders.keypair import Keypair
from solanatracker import SolanaTracker
import asyncio
import time

async def swap():
    start_time = time.time()

    keypair = Keypair.from_base58_string("YOUR_SECRET_KEY")  # Replace with your base58 private key

    solana_tracker = SolanaTracker(keypair, "https://rpc-mainnet.solanatracker.io/?api_key=YOUR_KEY")  # Your RPC here

    swap_response = await solana_tracker.get_swap_instructions(
        "So11111111111111111111111111111111111111112",  # From Token
        "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # To Token
        0.005,  # Amount to swap
        30,  # Slippage
        str(keypair.pubkey()),  # Payer public key
        0.005,  # Priority fee (Recommended while network is congested)
    )

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

if __name__ == "__main__":
    asyncio.run(swap())
```

## Key Features

- **Multi-hop routing** — up to 4-hop routes for optimal pricing
- **Dynamic slippage** — route-aware slippage calculation that accounts for multi-hop risk
- **Priority fee levels** — from cost-saving (Min/Low) to maximum speed (Turbo/UnsafeMax)
- **Yellowstone Jet TPU** — fast transaction sending with automatic resending and confirmation tracking
- **DEX filtering** — include or exclude specific DEXs per swap

## FAQ

#### Why should I use this API?

Raptor aggregates liquidity across 20+ Solana DEXs and finds optimal multi-hop routes in real time. Tokens are indexed the moment they become available, making it ideal for fast execution.

#### Is there a fee for using this API?

A 0.5% fee is charged on each successful transaction on this Legacy Swap API for unlimited usage, or use the Raptor Beta API directly for free. For public bots or high-volume sites, contact us via [Discord](https://discord.gg/JH2e9rR9fc) or email (solanatracker@yzylab.com) to get the fee reduced to 0.1%.

## Resources

- [Raptor DEX Aggregator Docs](https://docs.solanatracker.io/raptor/overview)
- [Solana Tracker](https://www.solanatracker.io)
- [Discord](https://discord.gg/JH2e9rR9fc)