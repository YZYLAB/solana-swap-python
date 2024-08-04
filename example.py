from solders.keypair import Keypair
from solanatracker import SolanaTracker
import asyncio
import time

async def swap():
    start_time = time.time()

    keypair = Keypair.from_base58_string("YOUR_SECRET_KEY")  # Replace with your base58 private key
    
    solana_tracker = SolanaTracker(keypair, "https://rpc.solanatracker.io/public?advancedTx=true")
    
    swap_response = await solana_tracker.get_swap_instructions(
        "So11111111111111111111111111111111111111112",  # From Token
        "9Vv199SR7VKVqbJmM5LoT26ZtC9bzrmqqxE3b4dfrubX",  # To Token
        0.0001,  # Amount to swap
        30,  # Slippage
        str(keypair.pubkey()),  # Payer public key
        0.00005,  # Priority fee (Recommended while network is congested)
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
        # Add retries or additional error handling as needed

if __name__ == "__main__":
    asyncio.run(swap())