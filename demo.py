"""Self-contained HermesProof v0.2 demonstration."""
import json
import os
import tempfile
from pathlib import Path

from tools import proof_report, proof_verify


def main():
    with tempfile.TemporaryDirectory(prefix="hermes-proof-demo-") as directory:
        root = Path(directory)
        os.environ["HERMES_PROOF_ROOT"] = str(root)
        os.environ["HERMES_HOME"] = str(root / "hermes-home")
        artifact = root / "deployment.txt"
        artifact.write_text("DEPLOYED\n", encoding="utf-8")
        previous = Path.cwd()
        try:
            os.chdir(root)
            request = [{"name": "deployment marker", "type": "file_contains",
                        "target": "deployment.txt", "expected": "DEPLOYED"}]
            positive = json.loads(proof_verify(request, label="positive demo"))
            artifact.write_text("BROKEN\n", encoding="utf-8")
            negative = json.loads(proof_verify(request, label="negative demo"))
            retrieved = json.loads(proof_report(negative["id"]))
        finally:
            os.chdir(previous)
        print(f"positive:  {positive['status']}")
        print(f"negative:  {negative['status']}")
        print(f"retrieved: {retrieved['status']} ({retrieved['id']})")


if __name__ == "__main__":
    main()
