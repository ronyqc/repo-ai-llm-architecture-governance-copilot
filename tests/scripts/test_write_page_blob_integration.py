from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from azure.storage.blob import BlobServiceClient


REPO_ROOT = Path(__file__).resolve().parents[2]
FUNCTION_APP_DIR = REPO_ROOT / "apps" / "document_processor_function"

sys.path.insert(0, str(FUNCTION_APP_DIR))

from processing.blob_writer import write_page_json_blob  # noqa: E402


def main() -> int:
    _load_local_settings()

    parser = argparse.ArgumentParser(
        description="Manual integration validation for write_page_json_blob using real Azure Blob Storage."
    )
    parser.add_argument(
        "--container",
        required=True,
        help="Target blob container name.",
    )
    parser.add_argument(
        "--directory",
        required=True,
        help="Target directory path inside the container.",
    )
    parser.add_argument(
        "--file-name",
        required=True,
        help="Logical file name. The script appends .json if missing.",
    )
    parser.add_argument(
        "--content-json",
        required=True,
        help="JSON string to write as blob content.",
    )
    args = parser.parse_args()

    try:
        content = json.loads(args.content_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid value for --content-json: {exc}") from exc

    result = write_page_json_blob(
        container_name=args.container,
        directory=args.directory,
        file_name=args.file_name,
        content=content,
    )

    print("=" * 80)
    print("WRITE RESULT")
    print(f"container_name: {result.container_name}")
    print(f"blob_name: {result.blob_name}")
    print(f"blob_url: {result.blob_url}")
    print(f"file_name: {result.file_name}")

    downloaded_payload = _download_blob_json(
        container_name=result.container_name,
        blob_name=result.blob_name,
    )

    print("-" * 80)
    print("READBACK VALIDATION")
    print("Blob content was downloaded successfully.")
    print(f"content_keys: {sorted(downloaded_payload.keys())}")
    print(json.dumps(downloaded_payload, ensure_ascii=False, indent=2))

    expected_file_name = args.file_name
    if not expected_file_name.lower().endswith(".json"):
        expected_file_name = f"{expected_file_name}.json"

    if downloaded_payload != content:
        raise SystemExit("Validation failed: downloaded payload does not match input JSON.")

    if result.file_name != expected_file_name:
        raise SystemExit("Validation failed: returned file_name does not match expected value.")

    print("-" * 80)
    print("INTEGRATION VALIDATION OK")
    return 0


def _download_blob_json(*, container_name: str, blob_name: str) -> dict:
    connection_string = _get_required_env(
        "AZURE_STORAGE_CONNECTION_STRING",
        "AzureWebJobsStorage",
    )
    service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = service_client.get_blob_client(
        container=container_name,
        blob=blob_name,
    )
    raw_content = blob_client.download_blob().readall().decode("utf-8")
    loaded_payload = json.loads(raw_content)
    if not isinstance(loaded_payload, dict):
        raise SystemExit("Validation failed: blob payload is not a JSON object.")
    return loaded_payload


def _load_local_settings() -> None:
    for candidate in (
        REPO_ROOT / ".env",
        FUNCTION_APP_DIR / ".env",
        FUNCTION_APP_DIR / "local.settings.json",
    ):
        if not candidate.is_file():
            continue

        if candidate.name.endswith(".json"):
            _load_local_settings_json(candidate)
            continue

        _load_dotenv_file(candidate)


def _load_local_settings_json(file_path: Path) -> None:
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {file_path}: {exc}") from exc

    values = payload.get("Values")
    if not isinstance(values, dict):
        return

    for key, value in values.items():
        if isinstance(key, str) and isinstance(value, str) and key not in os.environ:
            os.environ[key] = value


def _load_dotenv_file(file_path: Path) -> None:
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip("\"'")
        if normalized_key and normalized_key not in os.environ:
            os.environ[normalized_key] = normalized_value


def _get_required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()

    joined_names = ", ".join(names)
    raise SystemExit(f"Missing required environment variable. Expected one of: {joined_names}.")


if __name__ == "__main__":
    raise SystemExit(main())
