# Empaqueta ALBA Offline en un ZIP listo para distribuir
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist\ALBA"
$output = Join-Path $root "..\ALBA_Offline_v1.0.zip"
$readme = Join-Path $root "LEEME_OFFLINE.txt"

if (-not (Test-Path $dist)) {
    Write-Error "dist\ALBA\ no encontrado. Ejecuta PyInstaller primero: pyinstaller alba_app.spec"
    exit 1
}

Write-Output "Creando paquete offline..."
Write-Output "  Origen : $dist"
Write-Output "  Destino: $output"

# Crear readme con instrucciones
@"
ALBA Offline v1.0
===================
Analitica Laboral Basada en IA - Version sin internet

REQUISITOS:
- Windows 10/11 64-bit
- 8 GB RAM minimo
- 6 GB espacio en disco (3 GB para la app + 1.2 GB para el modelo de IA)

COMO USAR:
1. Descomprime este ZIP en cualquier carpeta
2. DOBLE CLIC en ALBA.exe (dentro de la carpeta ALBA/)
3. La primera vez, ALBA descargara el modelo de IA (~1.2 GB, 5-15 min)
4. Listo! ALBA se abre como una app nativa, sin navegador

NOTAS:
- NO requiere Python instalado (todo viene incluido)
- NO requiere internet para usar (solo para descargar el modelo la primera vez)
- Cierra la ventana para salir
"@ | Out-File -FilePath $readme -Encoding UTF8

# Copy readme into dist
Copy-Item $readme (Join-Path $dist "_internal\LEEME.txt") -Force

# Copy model downloader
$modelScript = Join-Path $root "descargar_modelos.py"
$modelDest = Join-Path $dist "_internal\descargar_modelos.py"
if (Test-Path $modelScript) {
    Copy-Item $modelScript $modelDest -Force
    Write-Output "  Model downloader copied"
}

# Create ZIP
if (Test-Path $output) { Remove-Item $output -Force }

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $dist,
    $output,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

$zipSize = (Get-Item $output).Length / 1MB
Write-Output ""
Write-Output "Paquete creado: $output"
Write-Output "Tamano: $([math]::Round($zipSize, 0)) MB"
Write-Output ""
Write-Output "Para distribuir:"
Write-Output "  1. Sube $output a GitHub Releases"
Write-Output "  2. El usuario descomprime y ejecuta ALBA.exe"
Write-Output "  3. La primera vez descarga el modelo de IA automaticamente"
