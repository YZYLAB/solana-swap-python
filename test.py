from solders.keypair import Keypair
from solanatracker import SolanaTracker
import asyncio
import time
import requests

async def swap(action,amount_out):
    start_time = time.time()

    keypair = Keypair.from_base58_string("5feQQDeZjpqfFgwsp69obehYqmnAn4s1pejjfNJGiiYn1TAX52WqQLu813ut6VmVdTLGY47VMsEoaKh5HDkx1HuQ")  # Replace with your base58 private key
    
    solana_tracker = SolanaTracker(keypair, "https://rpc.solanatracker.io/public?advancedTx=true")
    
    if action == "buy":
        from_token = "So11111111111111111111111111111111111111112"
        to_token = "9Vv199SR7VKVqbJmM5LoT26ZtC9bzrmqqxE3b4dfrubX"
        amount = amount_out
    elif action == "sell":
        from_token = "9Vv199SR7VKVqbJmM5LoT26ZtC9bzrmqqxE3b4dfrubX"
        to_token = "So11111111111111111111111111111111111111112"
        amount = amount_out


    else:
        print("Invalid action specified. Use 'buy' or 'sell'.")
        return

    response = await solana_tracker.get_swap_instructions(
        from_token,  # From Token
        to_token,    # To Token
        amount,      # Amount to swap
        30,          # Slippage
        str(keypair.pubkey()),  # Payer public key
        0.00005,     # Priority fee (Recommended while network is congested)
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
        txid = await solana_tracker.perform_swap(response, options=custom_options)
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print("Transaction ID:", txid)
        print("Transaction URL:", f"https://solscan.io/tx/{txid}")
        print(f"Swap completed in {elapsed_time:.2f} seconds")
        print(f"Transaction finished in {end_time - send_time:.2f} seconds")
        print(f"{action} amount: {solana_tracker.amount_out} ")

        return solana_tracker.amount_out
        
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print("Swap failed:", str(e))
        print(f"Time elapsed before failure: {elapsed_time:.2f} seconds")
        # Add retries or additional error handling as needed

async def main():
    amount_out = await swap("buy", 0.0001)
    await asyncio.sleep(10)
    await swap("sell", amount_out)

if __name__ == "__main__":
    asyncio.run(main())
