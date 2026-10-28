"""Push the committed app to a Hugging Face Space.

Usage: python deploy/push_hf_space.py <user>/<space-name>   (needs `hf auth login` first)
"""

import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
PATHS = ["src", "data/kb", "results", "frontend", "pyproject.toml", "requirements.lock"]


def main(repo_id: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # Committed files only, so local .env / DBs / caches never get uploaded.
        tar = subprocess.run(["git", "archive", "HEAD", *PATHS], cwd=ROOT,
                             capture_output=True, check=True)
        tarfile.open(fileobj=io.BytesIO(tar.stdout)).extractall(tmp)
        for name in ("Dockerfile", "README.md"):
            shutil.copy(ROOT / "deploy/hf_space" / name, Path(tmp) / name)

        api = HfApi()
        api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
        api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=tmp,
                          commit_message="Deploy from GitHub main", delete_patterns="*")
    print(f"https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main(sys.argv[1])
