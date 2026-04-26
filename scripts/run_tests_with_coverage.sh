#!/usr/bin/env bash
set -euo pipefail

.venv/Scripts/coverage.exe erase
.venv/Scripts/coverage.exe run --rcfile .coveragerc -m pytest --no-cov
.venv/Scripts/coverage.exe xml --rcfile .coveragerc
