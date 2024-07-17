import base64
import aiohttp
import asyncio
from solders.keypair import Keypair
from solders.rpc.responses import SendTransactionResp, GetSignatureStatusesResp, GetBlockHeightResp
from solders.transaction import Transaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Finalized, Processed
from solana.rpc.types import TxOpts
from typing import Dict, Optional, Union

class SolanaTracker:
    def __init__(self, keypair: Keypair, rpc: str):
        self.base_url = "https://swap-v2.solanatracker.io"
        self.rpc = rpc
        self.keypair = keypair
        self.amount_out = 0.00

    async def perform_swap(
        self,
        swap_response: Dict,
        options: Dict = {
            "send_options": {"skip_preflight": True},
            "confirmation_retries": 30,
            "confirmation_retry_timeout": 1000,
            "last_valid_block_height_buffer": 150,
            "commitment": "confirmed",
            "resend_interval": 1000,
            "confirmation_check_interval": 1000,
            "skip_confirmation_check": False,
        }
    ) -> Union[str, Exception]:
        commitment = options.get("commitment", "confirmed") 
        
        if commitment == "processed":
            commitment = Processed
        elif commitment == "confirmed":
            commitment = Confirmed
        elif commitment == "finalized":
            commitment = Finalized
        else:
            commitment = Confirmed

        self.connection = AsyncClient(self.rpc, commitment=commitment)

        try:
            serialized_transaction = base64.b64decode(swap_response["txn"])
            txn = Transaction.from_bytes(serialized_transaction)
            
            blockhash_resp = await self.connection.get_latest_blockhash()
            blockhash = blockhash_resp.value
            
            txn.sign([self.keypair], blockhash.blockhash)
            
            blockhash_with_expiry = {
                "blockhash": blockhash.blockhash,
                "last_valid_block_height": blockhash.last_valid_block_height,
            }

            return await self.transaction_sender_and_confirmation_waiter(
                serialized_transaction=bytes(txn),
                blockhash_with_expiry=blockhash_with_expiry,
                options=options
            )
        except Exception as e:
            return Exception(str(e))
        
    async def get_swap_instructions(
        self,
        from_token: str,
        to_token: str,
        from_amount: float,
        slippage: float,
        payer: str,
        priority_fee: Optional[float] = None,
        force_legacy: bool = False,
    ):
        params = {
            "from": from_token,
            "to": to_token,
            "fromAmount": str(from_amount),
            "slippage": str(slippage),
            "payer": payer,
            "forceLegacy": str(force_legacy).lower(),
        }
        if priority_fee is not None:
            params["priorityFee"] = str(priority_fee)
        url = f"{self.base_url}/swap"

        try:

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, ssl=False) as response:
                    print(params)
                    data = await response.json()

                    try:
                        
                        self.amount_out = round(float(data["rate"]["amountOut"]), 2)
                        print(f"data: {data}")
                    except Exception as error:
                        print("Error fetching swap instructions:", error)
                        raise error
                    
            data["forceLegacy"] = force_legacy
            return data
        except Exception as error:
            print("Error fetching swap instructions:", error)
            raise error

    async def transaction_sender_and_confirmation_waiter(
        self,
        serialized_transaction: bytes,
        blockhash_with_expiry: Dict,
        options: Dict
    ) -> Union[str, Exception]:
        send_options = options.get("send_options", {"skip_preflight": True})
        confirmation_retries = options.get("confirmation_retries", 30)
        confirmation_retry_timeout = options.get("confirmation_retry_timeout", 1000)
        last_valid_block_height_buffer = options.get("last_valid_block_height_buffer", 150)
        commitment = options.get("commitment", "processed")
        resend_interval = options.get("resend_interval", 1000)
        confirmation_check_interval = options.get("confirmation_check_interval", 1000)
        skip_confirmation_check = options.get("skip_confirmation_check", False)

        last_valid_block_height = blockhash_with_expiry["last_valid_block_height"] - last_valid_block_height_buffer

        retry_count = 0

        tx_opts = TxOpts(
            skip_preflight=send_options.get("skip_preflight", True),
            preflight_commitment=self.get_commitment(commitment),
            max_retries=send_options.get("max_retries", None)
        )

        response: SendTransactionResp = await self.connection.send_raw_transaction(
                    serialized_transaction,
                    tx_opts
        )
        signature = response.value

        if skip_confirmation_check:
            return str(signature)
        
        
        while retry_count <= confirmation_retries:
            try:
                status_response: GetSignatureStatusesResp = await self.connection.get_signature_statuses([signature])
                if status_response.value[0] is not None:
                    status = status_response.value[0]

                    if self.commitment_str_to_level(str(status.confirmation_status)) >= self.commitment_to_level(str(commitment)):
                        return str(signature)
                    if status.err:
                        return status.err

                await asyncio.sleep(confirmation_check_interval / 1000)

            except Exception as error:
                print("Error checking transaction status:", error)
                if retry_count == confirmation_retries or "Transaction expired" in str(error):
                    return Exception(str(error))

                retry_count += 1

                await asyncio.sleep(confirmation_retry_timeout / 1000)

                block_height_response: GetBlockHeightResp = await self.connection.get_block_height()
                if block_height_response.value > last_valid_block_height:
                    return Exception("Transaction expired")

        return Exception("Transaction failed after maximum retries")
    
    @staticmethod
    def commitment_to_level(commitment: str):
        if commitment == "confirmed":
            return 1
        elif commitment == "finalized":
            return 2
        elif commitment == "processed":
            return 0
        else:
            raise ValueError(f"Invalid commitment: {commitment}")
        
    @staticmethod
    def commitment_str_to_level(commitment: str):
        if commitment == "TransactionConfirmationStatus.Confirmed":
            return 1
        elif commitment == "TransactionConfirmationStatus.Finalized":
            return 2
        elif commitment == "TransactionConfirmationStatus.Processed":
            return 0
        else:
            raise ValueError(f"Invalid commitment: {commitment}")
        
    @staticmethod
    def get_commitment_str(commitment: str):
        if commitment == "confirmed":
            return "TransactionConfirmationStatus.Confirmed"
        elif commitment == "finalized":
            return "TransactionConfirmationStatus.Finalized"
        elif commitment == "processed":
            return "TransactionConfirmationStatus.Processed"
        else:
            raise ValueError(f"Invalid commitment: {commitment}")
        
    @staticmethod
    def get_commitment(commitment: str):
        if commitment == "confirmed":
            return "confirmed"
        elif commitment == "finalized":
            return "finalized"
        elif commitment == "processed":
            return "processed"
        else:
            raise ValueError(f"Invalid commitment: {commitment}")
        
    @staticmethod
    async def wait(seconds: float):
        await asyncio.sleep(seconds)