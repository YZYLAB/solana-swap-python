import base64
import time
import requests
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.signature import Signature
from solana.rpc.api import Client

class SolanaTracker:
    def __init__(self, keypair: Keypair, rpc: str, debug: bool = False):
        self.base_url = "https://swap-api.solanatracker.io"
        self.connection = Client(rpc)
        self.keypair = keypair
        self.debug = debug

    async def get_rate(self, from_token: str, to_token: str, amount: float, slippage: float) -> dict:
        params = {
            "from": from_token,
            "to": to_token,
            "amount": str(amount),
            "slippage": str(slippage),
        }
        url = f"{self.base_url}/rate"
        try:
            response = requests.get(url, params=params)
            return response.json()
        except Exception as error:
            print("Error fetching rate:", error)
            raise error

    async def get_swap_instructions(
        self,
        from_token: str,
        to_token: str,
        from_amount: float,
        slippage: float,
        payer: str,
        priority_fee: float = None,
        force_legacy: bool = False,
    ) -> dict:
        params = {
            "from": from_token,
            "to": to_token,
            "fromAmount": str(from_amount),
            "slippage": str(slippage),
            "payer": payer,
            "forceLegacy": str(force_legacy).lower(),
        }
        if priority_fee:
            params["priorityFee"] = str(priority_fee)
        url = f"{self.base_url}/swap"
        try:
            response = requests.get(url, params=params)
            return response.json()
        except Exception as error:
            print("Error fetching swap instructions:", error)
            raise error

    async def perform_swap(self, swap_response: dict) -> str:
        try:
            serialized_transaction = base64.b64decode(swap_response["txn"])
            txn = Transaction.from_bytes(serialized_transaction)
            blockhash = self.connection.get_latest_blockhash().value.blockhash

            txn.sign([self.keypair], blockhash)
            response = self.connection.send_raw_transaction(bytes(txn))
            return self.confirm_transaction(str(response.value))
        except Exception as e:
            return False

    def confirm_transaction(self, txid: str, max_retries: int = 60, retry_interval: float = 1.0) -> str:
        retries = 0
        while retries < max_retries:
            try:
                resp = self.connection.get_signature_statuses([Signature.from_string(txid)], True)
                if resp.value is not None and len(resp.value) > 0:
                    if self.debug and resp.value[0] is not None and resp.value[0].confirmations:
                        print(f"Confirmations: {resp.value[0].confirmations}")
                    if resp.value[0] is not None and resp.value[0].confirmation_status is not None and str(resp.value[0].confirmation_status) == "TransactionConfirmationStatus.Finalized":
                        break
            except Exception as e:
                print(f"Error checking transaction status: {e}")
            retries += 1
            time.sleep(retry_interval)
        if retries >= max_retries:
            raise TimeoutError(f"Transaction {txid} was not confirmed after {max_retries} retries")
        else:
            return txid