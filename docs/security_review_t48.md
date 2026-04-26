# T48 Security Review

## Scope

- Static analysis over `src/` and `apps/` with `bandit`
- Dependency vulnerability review over the project virtual environment with `pip-audit`

## Reproducible commands

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -r apps\document_processor_function\requirements.txt
.venv\Scripts\bandit.exe -c bandit.yaml -r src apps -f json -o reports\bandit-report.json
.venv\Scripts\pip-audit.exe --path .venv\Lib\site-packages --cache-dir reports\pip-audit-cache --format=json -o reports\pip-audit-report.json
.venv\Scripts\coverage.exe erase
.venv\Scripts\coverage.exe run --rcfile .coveragerc -m pytest --no-cov
.venv\Scripts\coverage.exe xml --rcfile .coveragerc
```

## Findings treatment

- `B405` / `B314` on DOCX parsing: fixed by replacing `xml.etree.ElementTree` with `defusedxml.ElementTree`.
- `B310` on health checks: accepted after explicit HTTPS URL validation before `urlopen`; the calls are limited to configured Azure endpoints.

## Accepted risks / false positives

- `starlette` vulnerability on `FileResponse`/`StaticFiles`: the backend and Function App do not expose those primitives in current code paths, so the finding is documented as low practical exposure for this MVP.
- `pip` and `setuptools` findings reported by `pip-audit` belong to local packaging tooling, not to the application runtime declared in `requirements.txt`; keep the developer environment updated separately.
- Coverage generation on Windows is executed through `coverage run` instead of the default `pytest-cov` hook because the latter failed while persisting `.coverage` in this repository.
