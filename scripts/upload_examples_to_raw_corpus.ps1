param(
    [string]$ContainerName = $env:AZURE_STORAGE_CONTAINER
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

$ExamplesSourceDir = if ($env:EXAMPLES_SOURCE_DIR) { $env:EXAMPLES_SOURCE_DIR } else { Join-Path $RepoRoot "corpus/examples" }
$TemplatesSourceDir = if ($env:TEMPLATES_SOURCE_DIR) { $env:TEMPLATES_SOURCE_DIR } else { Join-Path $RepoRoot "corpus/templates" }
$ExamplesDestinationPrefix = if ($env:EXAMPLES_DESTINATION_PREFIX) { $env:EXAMPLES_DESTINATION_PREFIX } else { "raw-corpus" }
$TemplatesDestinationPrefix = if ($env:TEMPLATES_DESTINATION_PREFIX) { $env:TEMPLATES_DESTINATION_PREFIX } else { "raw-corpus-templates" }
$UploadTemplates = if ($env:UPLOAD_TEMPLATES) { $env:UPLOAD_TEMPLATES } else { "false" }

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI ('az') no esta instalado o no esta en el PATH."
}

$EnvFile = Join-Path $RepoRoot ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -eq 2 -and -not [string]::IsNullOrWhiteSpace($parts[0])) {
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim())
        }
    }
}

$ConnectionString = $env:AZURE_STORAGE_CONNECTION_STRING
if (-not $ContainerName) {
    $ContainerName = $env:AZURE_STORAGE_CONTAINER
}

if (-not $ConnectionString) {
    throw "Falta AZURE_STORAGE_CONNECTION_STRING en el entorno o en .env."
}

if (-not $ContainerName) {
    throw "Debes indicar el contenedor. Ejemplo: .\scripts\upload_examples_to_raw_corpus.ps1 -ContainerName raw-corpus"
}

function Upload-Directory {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$DestinationPrefix,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path $SourceDir)) {
        throw "No existe el directorio fuente '$SourceDir'."
    }

    Write-Host "Subiendo $Label desde: $SourceDir"
    Write-Host "Contenedor destino: $ContainerName"
    Write-Host "Prefijo destino: $DestinationPrefix"

    az storage blob upload-batch `
        --connection-string $ConnectionString `
        --destination $ContainerName `
        --source $SourceDir `
        --destination-path $DestinationPrefix `
        --overwrite true `
        --only-show-errors
}

Upload-Directory -SourceDir $ExamplesSourceDir -DestinationPrefix $ExamplesDestinationPrefix -Label "examples"

if ($UploadTemplates.ToLower() -eq "true") {
    Upload-Directory -SourceDir $TemplatesSourceDir -DestinationPrefix $TemplatesDestinationPrefix -Label "templates"
}

Write-Host "Carga completada."
