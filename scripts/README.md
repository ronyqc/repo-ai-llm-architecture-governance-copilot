# Scripts

## upload_examples_to_raw_corpus.sh

Sube los archivos de `corpus/examples` a Azure Blob Storage preservando la estructura de carpetas bajo el prefijo `raw-corpus/`.

Ejemplo:

```bash
chmod +x scripts/upload_examples_to_raw_corpus.sh
AZURE_STORAGE_CONTAINER=my-container ./scripts/upload_examples_to_raw_corpus.sh
```

Tambien acepta el nombre del contenedor como primer argumento:

```bash
./scripts/upload_examples_to_raw_corpus.sh my-container
```

Por defecto:

- `corpus/examples` se sube a `raw-corpus/`
- `corpus/templates` no se sube

Para subir tambien templates:

```bash
UPLOAD_TEMPLATES=true AZURE_STORAGE_CONTAINER=my-container ./scripts/upload_examples_to_raw_corpus.sh
```

Variables utiles:

- `EXAMPLES_SOURCE_DIR`
- `TEMPLATES_SOURCE_DIR`
- `EXAMPLES_DESTINATION_PREFIX`
- `TEMPLATES_DESTINATION_PREFIX`
- `UPLOAD_TEMPLATES`

## upload_examples_to_raw_corpus.ps1

Version para PowerShell, util si trabajas en Windows sin `bash` o sin WSL configurado.

Ejemplo:

```powershell
$env:AZURE_STORAGE_CONNECTION_STRING="<tu-connection-string>"
.\scripts\upload_examples_to_raw_corpus.ps1 -ContainerName "raw-corpus"
```

Para subir tambien templates:

```powershell
$env:UPLOAD_TEMPLATES="true"
.\scripts\upload_examples_to_raw_corpus.ps1 -ContainerName "raw-corpus"
```
