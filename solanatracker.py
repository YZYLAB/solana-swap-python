import base64
import aiohttp
import asyncio
import logging
from solders.keypair import Keypair
from solders.rpc.responses import (
    SendTransactionResp,
    GetSignatureStatusesResp,
    GetBlockHeightResp,
)
from solders.transaction_status import TransactionConfirmationStatus
from solders.transaction import TransactionError, VersionedTransaction
from solders.hash import Hash
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed, Confirmed, Finalized, Commitment as SolanaCommitment
import solana.rpc.commitment # For robust isinstance check
from solana.rpc.types import TxOpts
from typing import Dict, Optional, Union, Any, List, Literal, TypedDict

# Module-level logger, used by helper functions like _string_to_solana_commitment
# Users can configure this logger via logging.getLogger(__name__) if needed.
# By default, if no handlers are configured by the application, these logs won't appear.
logger = logging.getLogger(__name__)

# --- TypedDicts for Options ---
class SendOptions(TypedDict, total=False):
    """Options for sending a transaction."""
    skip_preflight: bool
    preflight_commitment: Union[str, SolanaCommitment] 
    max_retries: Optional[int]

class TransactionOptions(TypedDict, total=False):
    """Options for the transaction lifecycle."""
    send_options: SendOptions
    confirmation_retries: int
    confirmation_retry_timeout_ms: int 
    confirmation_retry_timeout: int # Old key
    last_valid_block_height_buffer: int
    commitment: Union[str, SolanaCommitment] 
    resend_interval_ms: int # Old key (not actively used)
    resend_interval: int 
    confirmation_check_interval_ms: int
    confirmation_check_interval: int # Old key
    skip_confirmation_check: bool

# --- Default Option Values ---
DEFAULT_SEND_OPTIONS: SendOptions = {
    "skip_preflight": True,
    "preflight_commitment": Confirmed, 
}

DEFAULT_TRANSACTION_OPTIONS: TransactionOptions = {
    "send_options": DEFAULT_SEND_OPTIONS.copy(),
    "confirmation_retries": 30,
    "confirmation_retry_timeout_ms": 1000,
    "last_valid_block_height_buffer": 150,
    "commitment": Confirmed,
    "resend_interval_ms": 1000, 
    "confirmation_check_interval_ms": 1000,
    "skip_confirmation_check": False,
}

# --- Custom Exceptions ---
class SolanaTrackerError(Exception):
    """Base exception for errors originating from the SolanaTracker class."""
    pass

class TransactionFailedError(SolanaTrackerError):
    """Raised when a transaction fails with a specific on-chain error."""
    def __init__(self, signature: str, error_details: Union[TransactionError, Any]):
        self.signature = signature
        self.error_details = error_details
        details_repr = repr(error_details)
        super().__init__(f"Transaction {signature} failed: {details_repr}")

class TransactionExpiredError(SolanaTrackerError):
    """Raised when a transaction expires before confirmation."""
    def __init__(self, signature: str, message: str = "Transaction expired"):
        self.signature = signature
        super().__init__(f"Transaction {signature}: {message}")

class TransactionConfirmationTimeoutError(SolanaTrackerError):
    """Raised when a transaction fails to confirm within the allocated retries."""
    def __init__(self, signature: str, message: str = "Transaction confirmation timeout"):
        self.signature = signature
        super().__init__(f"Transaction {signature}: {message}")

# --- Helper for Commitment String to SolanaCommitment Object ---
def _string_to_solana_commitment(s: Union[str, SolanaCommitment]) -> SolanaCommitment:
    
    s_str = str(s)
    s_lower = s_str.lower() 
    if s_lower == "processed":
        return Processed
    elif s_lower == "confirmed":
        return Confirmed
    elif s_lower == "finalized":
        return Finalized
    # Use the module-level logger for this helper function
    logger.warning(f"Invalid commitment string '{s_str}', defaulting to Confirmed.")
    return Confirmed

def _solana_commitment_to_transaction_confirmation_status(
    c: SolanaCommitment
) -> TransactionConfirmationStatus:
    if c == Processed:
        return TransactionConfirmationStatus.Processed
    elif c == Confirmed:
        return TransactionConfirmationStatus.Confirmed
    elif c == Finalized:
        return TransactionConfirmationStatus.Finalized
    raise ValueError(f"Cannot map SolanaCommitment '{c}' to TransactionConfirmationStatus.")


class SolanaTracker:
    BASE_URL = "https://swap-v2.solanatracker.io"

    def __init__(self, 
                 keypair: Keypair, 
                 rpc_url: str, 
                 proxy_url: Optional[str] = None,
                 logging_level: Union[int, str] = "OFF" # Default to OFF
                ):
        self.keypair = keypair
        self.rpc_url = rpc_url
        self.proxy_url = proxy_url
        
        # Initialize instance-specific logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Set logging level for this instance
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "OFF": logging.CRITICAL + 1  # Effectively disable logging for this instance by default
        }
        if isinstance(logging_level, str):
            actual_level = level_map.get(logging_level.upper(), logging.CRITICAL + 1)
        elif isinstance(logging_level, int):
            actual_level = logging_level
        else:
            actual_level = logging.CRITICAL + 1 # Default to OFF if type is unexpected
            
        self.logger.setLevel(actual_level)
        
        # Note: This class does not add handlers to its logger.
        # The application using this class is responsible for configuring
        # logging handlers (e.g., StreamHandler) if output is desired.
        if actual_level <= logging.DEBUG: # Log only if very verbose debugging is on
             self.logger.debug(f"SolanaTracker instance initialized with logging level: {logging.getLevelName(actual_level)}")


    async def get_swap_instructions(
        self,
        from_token: str,
        to_token: str,
        from_amount: float,
        slippage: float,
        payer: str,
        priority_fee: Optional[float] = None,
        force_legacy: bool = False,
    ) -> Dict[str, Any]:
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
        url = f"{self.BASE_URL}/swap"
        self.logger.info(f"Fetching swap instructions from {url} with params: {params}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, proxy=self.proxy_url) as response:
                    response.raise_for_status()
                    data = await response.json()
            data["forceLegacy"] = force_legacy
            self.logger.debug(f"Received swap instructions: {data}")
            return data
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP error fetching swap instructions: {url}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error fetching swap instructions: {e}", exc_info=True)
            raise

    async def perform_swap(
        self,
        swap_response: Dict[str, Any],
        options: Optional[TransactionOptions] = None,
    ) -> Union[str, Exception]:
        # --- Options Resolution with Backward Compatibility ---
        current_tx_options: Dict[str, Any] = {} 
        for k_default, v_default in DEFAULT_TRANSACTION_OPTIONS.items(): # type: ignore
            if isinstance(v_default, dict):
                current_tx_options[k_default] = v_default.copy()
            else:
                current_tx_options[k_default] = v_default
        
        if options:
            if "send_options" in options and options["send_options"] is not None:
                current_tx_options["send_options"].update(options["send_options"])

            for key, value in options.items():
                if key != "send_options": 
                    current_tx_options[key] = value
            
            renamed_keys_map = {
                "confirmation_retry_timeout": "confirmation_retry_timeout_ms",
                "confirmation_check_interval": "confirmation_check_interval_ms",
                "resend_interval": "resend_interval_ms",
            }
            for old_key, new_key in renamed_keys_map.items():
                if old_key in options and new_key not in options: 
                    if old_key in current_tx_options: 
                        current_tx_options[new_key] = current_tx_options.pop(old_key)
        
        main_commitment_input = current_tx_options.get("commitment", DEFAULT_TRANSACTION_OPTIONS["commitment"])
        main_commitment_obj = _string_to_solana_commitment(main_commitment_input) # type: ignore
        current_tx_options["commitment"] = main_commitment_obj 

        preflight_for_tx_opts_obj: SolanaCommitment
        user_set_preflight_explicitly = (
            options and "send_options" in options and options["send_options"] and
            "preflight_commitment" in options["send_options"]
        )

        if user_set_preflight_explicitly:
            preflight_input = options["send_options"]["preflight_commitment"] # type: ignore
            preflight_for_tx_opts_obj = _string_to_solana_commitment(preflight_input)
        else:
            preflight_for_tx_opts_obj = main_commitment_obj
        
        if "send_options" in current_tx_options and current_tx_options["send_options"] is not None:
            current_tx_options["send_options"]["preflight_commitment"] = preflight_for_tx_opts_obj
        else: 
            self.logger.warning("send_options missing in current_tx_options during preflight_commitment setup.")
            current_tx_options["send_options"] = {"preflight_commitment": preflight_for_tx_opts_obj}

        self.logger.info(f"Attempting swap. Client commitment: {main_commitment_obj}, TxOpts preflight: {preflight_for_tx_opts_obj}")
        self.logger.debug(f"Resolved transaction options for perform_swap: {current_tx_options}")

        async with AsyncClient(self.rpc_url, commitment=main_commitment_obj) as connection:
            try:
                if "txn" not in swap_response:
                    err_msg = "Swap response dictionary must contain a 'txn' field."
                    self.logger.error(err_msg)
                    return ValueError(err_msg)

                serialized_txn_b64 = swap_response["txn"]
                decoded_txn_bytes = base64.b64decode(serialized_txn_b64)
                txn = VersionedTransaction.from_bytes(decoded_txn_bytes)
                self.logger.info(f"Deserialized versioned transaction (version: {txn.version()})")

                # Re-sign the transaction with our keypair
                # The message already contains the blockhash set by the API
                signed_txn = VersionedTransaction(txn.message, [self.keypair])
                self.logger.info("Transaction signed.")

                # Fetch last_valid_block_height for expiry tracking
                self.logger.info("Fetching latest blockhash for expiry tracking.")
                blockhash_resp = await connection.get_latest_blockhash()
                if not blockhash_resp.value:
                    err_msg = "Failed to fetch latest blockhash."
                    self.logger.error(err_msg)
                    return RuntimeError(err_msg)
                
                last_valid_block_height = blockhash_resp.value.last_valid_block_height
                self.logger.info(f"LVBH for expiry: {last_valid_block_height}")

                blockhash_details_for_expiry = {
                    "blockhash": txn.message.recent_blockhash,
                    "last_valid_block_height": last_valid_block_height,
                }
                
                final_options_for_waiter = current_tx_options 
                
                self.logger.debug(f"Signed transaction ready to send.") 
                return await self._transaction_sender_and_confirmation_waiter(
                    connection=connection,
                    signed_transaction_bytes=bytes(signed_txn), 
                    blockhash_with_expiry=blockhash_details_for_expiry,
                    options=final_options_for_waiter, # type: ignore 
                    tx_preflight_commitment_for_tx_opts=preflight_for_tx_opts_obj
                )
            except base64.binascii.Error as b64e:
                self.logger.error(f"Base64 decoding failed: {b64e}")
                return ValueError(f"Invalid base64 transaction string: {b64e}")
            except Exception as e: 
                self.logger.error(f"Error in perform_swap setup: {e}", exc_info=True)
                return e 

    async def _transaction_sender_and_confirmation_waiter(
        self,
        connection: AsyncClient,
        signed_transaction_bytes: bytes,
        blockhash_with_expiry: Dict[str, Any],
        options: TransactionOptions, 
        tx_preflight_commitment_for_tx_opts: SolanaCommitment
    ) -> Union[str, Exception]:
        
        send_opts_dict = options.get("send_options", DEFAULT_SEND_OPTIONS)
        
        tx_opts = TxOpts(
            skip_preflight=send_opts_dict.get("skip_preflight", DEFAULT_SEND_OPTIONS["skip_preflight"]), # type: ignore
            preflight_commitment=tx_preflight_commitment_for_tx_opts, 
            max_retries=send_opts_dict.get("max_retries") # type: ignore
        )

        effective_lvbh = (
            blockhash_with_expiry["last_valid_block_height"] -
            options.get("last_valid_block_height_buffer", DEFAULT_TRANSACTION_OPTIONS["last_valid_block_height_buffer"]) # type: ignore
        )
        
        desired_commitment_obj: SolanaCommitment = options["commitment"] # type: ignore
        desired_conf_status_enum = _solana_commitment_to_transaction_confirmation_status(desired_commitment_obj)

        try: 
            self.logger.info(f"Sending transaction with TxOpts: {tx_opts}")
            resp: SendTransactionResp = await connection.send_raw_transaction(
                signed_transaction_bytes, opts=tx_opts
            )
            signature = resp.value
            self.logger.info(f"Transaction sent. Signature: {signature}")

            if options.get("skip_confirmation_check"):
                self.logger.info("Skipping confirmation check.")
                return str(signature)

            retries = options.get("confirmation_retries", DEFAULT_TRANSACTION_OPTIONS["confirmation_retries"]) # type: ignore
            check_interval_s = options.get("confirmation_check_interval_ms", DEFAULT_TRANSACTION_OPTIONS["confirmation_check_interval_ms"]) / 1000.0 # type: ignore
            
            self.logger.info(f"Waiting for confirmation for {signature} (desired: {desired_commitment_obj}, up to {retries} retries)...") # type: ignore

            for attempt in range(retries + 1): # type: ignore
                self.logger.debug(f"Conf check attempt {attempt + 1}/{retries + 1} for {signature}") # type: ignore
                
                if attempt > 0 or check_interval_s > 0 : 
                     await asyncio.sleep(check_interval_s)

                try:
                    status_resp: GetSignatureStatusesResp = await connection.get_signature_statuses([signature])
                    if status_resp.value and status_resp.value[0] is not None:
                        sig_status = status_resp.value[0]
                        self.logger.debug(f"Sig {signature} status: {sig_status.confirmation_status}, err: {sig_status.err}")

                        if sig_status.err:
                            err_obj = TransactionFailedError(str(signature), sig_status.err)
                            self.logger.error(f"TransactionFailedError created: {err_obj}")
                            return err_obj

                        if sig_status.confirmation_status:
                            current_enum = sig_status.confirmation_status
                            if self._is_commitment_level_sufficient(current_enum, desired_conf_status_enum):
                                self.logger.info(f"Tx {signature} confirmed: {current_enum}")
                                return str(signature)
                    else:
                        self.logger.debug(f"Status for {signature} not yet available or null.")

                except Exception as status_e: 
                    self.logger.warning(f"Error during status check for {signature} (attempt {attempt + 1}): {status_e}")
                    retry_timeout_s = options.get("confirmation_retry_timeout_ms", DEFAULT_TRANSACTION_OPTIONS["confirmation_retry_timeout_ms"]) / 1000.0 # type: ignore
                    await asyncio.sleep(retry_timeout_s)

                current_block_height_resp: GetBlockHeightResp = await connection.get_block_height(commitment=Processed)
                current_bh = current_block_height_resp.value
                self.logger.debug(f"Current BH: {current_bh}. Tx valid until: {effective_lvbh}")
                if current_bh < effective_lvbh:
                    err_obj = TransactionExpiredError(str(signature), f"Expired at BH {current_bh}")
                    self.logger.error(err_obj)
                    return err_obj
            
            timeout_err_obj = TransactionConfirmationTimeoutError(str(signature))
            self.logger.error(timeout_err_obj)
            return timeout_err_obj

        except Exception as e: 
            self.logger.error(f"Error in tx sender/waiter for signature {getattr(e, 'signature', 'N/A')}: {e}", exc_info=True)
            if isinstance(e, SolanaTrackerError): 
                return e
            return Exception(f"Failed during transaction processing: {e}")

    @staticmethod
    def _commitment_level_to_int(status: TransactionConfirmationStatus) -> int:
        """Convert a TransactionConfirmationStatus to a comparable integer.
        
        Uses string comparison since newer solders versions make the enum unhashable.
        """
        s = str(status)
        if s == str(TransactionConfirmationStatus.Processed):
            return 0
        elif s == str(TransactionConfirmationStatus.Confirmed):
            return 1
        elif s == str(TransactionConfirmationStatus.Finalized):
            return 2
        return -1

    @staticmethod
    def _is_commitment_level_sufficient(
        current_status: TransactionConfirmationStatus,
        desired_status: TransactionConfirmationStatus
    ) -> bool:
        current_level = SolanaTracker._commitment_level_to_int(current_status)
        desired_level = SolanaTracker._commitment_level_to_int(desired_status)

        if current_level < 0 or desired_level < 0:
            logger.warning(f"Unknown commitment status in comparison. Current: {current_status}, Desired: {desired_status}")
            return False
        return current_level >= desired_level

    @staticmethod
    async def wait(seconds: float):
        if seconds <= 0: return
        # Use module-level logger here
        logger.debug(f"Waiting for {seconds} seconds...")
        await asyncio.sleep(seconds)

