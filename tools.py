"""Deterministic verification engine. No LLM judging, shell execution or credentials."""
try:
    from .handlers import proof_report, proof_verify
except ImportError:  # Standalone plugin-loader/test compatibility.
    from handlers import proof_report, proof_verify

__all__ = ["proof_verify", "proof_report"]
