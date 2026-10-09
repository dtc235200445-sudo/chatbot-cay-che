"""
Đẩy backend lên Hugging Face Space (Docker) và khai báo biến môi trường của Space.

Chỉ đẩy những gì backend cần (không đẩy frontend, docs, kết quả đánh giá, .env). Space tự build lại Docker sau mỗi lần đẩy.

Biến môi trường (GitHub Actions truyền vào từ Secrets/Variables):
  HF_TOKEN       token Hugging Face có quyền write (bắt buộc)
  HF_SPACE       tên Space dạng "<user>/<space>", ví dụ "hieuvh/tea-scholar-api" (bắt buộc)
  GROQ_API_KEY, DATABASE_URL, SECRET_KEY, GEMINI_API_KEY   -> đặt thành Secret của Space (nếu có)
  CORS_ORIGINS, LLM_FALLBACKS                              -> đặt thành Variable của Space (nếu có)

Chạy tay: HF_TOKEN=... HF_SPACE=user/space python scripts/deploy/push_to_hf_space.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ["backend", "rag", "database", "data", "scripts/deploy", "requirements.txt", "Dockerfile", ".dockerignore"]
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "evaluation", "*.db", "chroma_db", ".pytest_cache")
SECRETS = ["GROQ_API_KEY", "DATABASE_URL", "SECRET_KEY", "GEMINI_API_KEY"]
VARIABLES = ["CORS_ORIGINS", "LLM_FALLBACKS"]


def stage(dst: Path) -> None:
    for item in INCLUDE:
        src = ROOT / item
        if src.is_dir():
            shutil.copytree(src, dst / item, ignore=SKIP)
        else:
            (dst / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / item)
    # README.md của Space phải có phần khai báo YAML (sdk: docker, app_port) ở đầu
    shutil.copy2(ROOT / "scripts" / "deploy" / "space_README.md", dst / "README.md")


def main() -> None:
    token, space = os.environ.get("HF_TOKEN"), os.environ.get("HF_SPACE")
    if not token or not space:
        sys.exit("Thiếu HF_TOKEN hoặc HF_SPACE")
    api = HfApi(token=token)
    api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)

    for key in SECRETS:
        if os.environ.get(key):
            api.add_space_secret(space, key, os.environ[key])
            print(f"Secret {key}: đã cập nhật")
    for key in VARIABLES:
        if os.environ.get(key):
            api.add_space_variable(space, key, os.environ[key])
            print(f"Variable {key} = {os.environ[key]}")

    with tempfile.TemporaryDirectory() as tmp:
        stage(Path(tmp))
        # delete_patterns="*": xóa trên Space những file không còn trong bản đẩy lên, để Space khớp với repo
        info = api.upload_folder(folder_path=tmp, repo_id=space, repo_type="space", delete_patterns="*",
                                 commit_message=f"Deploy từ GitHub {os.environ.get('GITHUB_SHA', 'local')[:7]}")
    print("Đã đẩy lên Space:", info.commit_url if hasattr(info, "commit_url") else info)
    print(f"Space đang build lại: https://huggingface.co/spaces/{space}")


if __name__ == "__main__":
    main()
