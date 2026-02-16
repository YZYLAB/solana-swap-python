from solders.keypair import Keypair
from solanatracker import SolanaTracker
import asyncio
import time
import logging

async def swap():
    start_time = time.time()

    keypair = Keypair.from_base58_string ("PRIVATE_KEY_DONT_SHARE")  # Replace with your base58 private key
    
    # Get your api key from https://www.solanatracker.io/solana-rpc
    solana_tracker = SolanaTracker(keypair, "https://rpc-mainnet.solanatracker.io/?api_key=YOUR_KEY", None, logging.INFO)
    
    swap_response = await solana_tracker.get_swap_instructions(
        "So11111111111111111111111111111111111111112",  # From Token
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # To Token
        0.0001,  # Amount to swap
        30,  # Slippage
        str(keypair.pubkey()),  # Payer public key
        0.00005,  # Priority fee (Recommended while network is congested)
    )

    
    # Define custom options
    custom_options = {
        "send_options": {"skip_preflight": True, "max_retries": 0},
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