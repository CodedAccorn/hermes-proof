"""HermesProof native plugin registration (v0.2 tool-only release)."""
try:
    from . import schemas, tools
except ImportError:  # Standalone plugin-loader/test compatibility.
    import schemas
    import tools


def register(ctx):
    ctx.register_tool(name='proof_verify', toolset='hermes-proof', schema=schemas.VERIFY, handler=tools.proof_verify)
    ctx.register_tool(name='proof_report', toolset='hermes-proof', schema=schemas.REPORT, handler=tools.proof_report)
