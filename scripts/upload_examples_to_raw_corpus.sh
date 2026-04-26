#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXAMPLES_SOURCE_DIR="${EXAMPLES_SOURCE_DIR:-${REPO_ROOT}/corpus/examples}"
TEMPLATES_SOURCE_DIR="${TEMPLATES_SOURCE_DIR:-${REPO_ROOT}/corpus/templates}"
EXAMPLES_DESTINATION_PREFIX="${EXAMPLES_DESTINATION_PREFIX:-raw-corpus}"
TEMPLATES_DESTINATION_PREFIX="${TEMPLATES_DESTINATION_PREFIX:-raw-corpus-templates}"
UPLOAD_TEMPLATES="${UPLOAD_TEMPLATES:-false}"

if ! command -v az >/dev/null 2>&1; then
  echo "Error: Azure CLI ('az') no esta instalado o no esta en el PATH." >&2
  exit 1
fi

if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

AZURE_STORAGE_CONNECTION_STRING="${AZURE_STORAGE_CONNECTION_STRING:-}"
AZURE_STORAGE_CONTAINER="${AZURE_STORAGE_CONTAINER:-${1:-}}"

if [[ -z "${AZURE_STORAGE_CONNECTION_STRING}" ]]; then
  echo "Error: falta AZURE_STORAGE_CONNECTION_STRING en el entorno o en .env." >&2
  exit 1
fi

if [[ -z "${AZURE_STORAGE_CONTAINER}" ]]; then
  echo "Uso: AZURE_STORAGE_CONTAINER=<contenedor> $0" >&2
  echo "O tambien: $0 <contenedor>" >&2
  exit 1
fi

if [[ ! -d "${EXAMPLES_SOURCE_DIR}" ]]; then
  echo "Error: no existe el directorio fuente '${EXAMPLES_SOURCE_DIR}'." >&2
  exit 1
fi

upload_directory() {
  local source_dir="$1"
  local destination_prefix="$2"
  local label="$3"

  if [[ ! -d "${source_dir}" ]]; then
    echo "Error: no existe el directorio fuente '${source_dir}'." >&2
    exit 1
  fi

  echo "Subiendo ${label} desde: ${source_dir}"
  echo "Contenedor destino: ${AZURE_STORAGE_CONTAINER}"
  echo "Prefijo destino: ${destination_prefix}"

  az storage blob upload-batch \
    --connection-string "${AZURE_STORAGE_CONNECTION_STRING}" \
    --container-name "${AZURE_STORAGE_CONTAINER}" \
    --source "${source_dir}" \
    --destination-path "${destination_prefix}" \
    --overwrite true \
    --only-show-errors
}

upload_directory "${EXAMPLES_SOURCE_DIR}" "${EXAMPLES_DESTINATION_PREFIX}" "examples"

if [[ "${UPLOAD_TEMPLATES,,}" == "true" ]]; then
  upload_directory "${TEMPLATES_SOURCE_DIR}" "${TEMPLATES_DESTINATION_PREFIX}" "templates"
fi

echo "Carga completada."
