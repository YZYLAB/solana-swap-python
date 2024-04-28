from solders.keypair import Keypair
from solanatracker import SolanaTracker

async def swap():
    keypair = Keypair.from_base58_string("YOUR_SECRET_KEY")

    solana_tracker = SolanaTracker(keypair, "https://rpc.solanatracker.io/public?advancedTx=true")

    swap_response = await solana_tracker.get_swap_instructions(
        "So11111111111111111111111111111111111111112",  # From Token
        "667w6y7eH5tQucYQXfJ2KmiuGBE8HfYnqqbjLNSw7yww",  # To Token
        0.0005,  # Amount to swap
        10,  # Slippage
        str(keypair.pubkey()),  # Payer public key
        0.000005,  # Priority fee (Recommended while network is congested)
        True,  # Force legacy transaction for Jupiter
    )

    txid = await solana_tracker.perform_swap(swap_response)

    # Returns txid when the swap is successful or raises an exception if the swap fails
    print("Transaction ID:", txid)
    print("Transaction URL:", f"https://explorer.solana.com/tx/{txid}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(swap())