"""
==============================================================================
  QUANT ENGINE — CREDENTIAL MASKING & SECURITY UTILITY
==============================================================================
"""

def mask_credential(secret_str: str) -> str:
    """Masks sensitive API keys for safe logging and UI display"""
    if not secret_str or len(secret_str) < 8:
        return "********"
    return secret_str[:4] + "..." + secret_str[-4:]
