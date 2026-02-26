#!/usr/bin/env python3
"""One-time helper to download the local LLM model."""

import subprocess
from pathlib import Path


MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


def main():
    subprocess.run(
        [
            "huggingface-cli",
            "download",
            "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
            "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "--local-dir",
            str(MODEL_DIR),
        ],
        check=True,
    )
    print(f"Model saved to {MODEL_DIR}")


if __name__ == "__main__":
    main()
