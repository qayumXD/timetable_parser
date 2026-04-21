#!/usr/bin/env python3
"""One-time helper to download the local LLM model."""

from pathlib import Path

from huggingface_hub import hf_hub_download


MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


def main():
    path = hf_hub_download(
        repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        local_dir=str(MODEL_DIR),
    )
    print(f"Model saved to {path}")


if __name__ == "__main__":
    main()
