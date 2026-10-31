# Рендер слайдов .pptx в PNG для визуального контроля.
# Приоритет: PowerPoint (COM, Windows) -> LibreOffice (soffice) -> ошибка с подсказкой.
#
# Использование:
#   powershell -ExecutionPolicy Bypass -File export_images.ps1 -Deck out.pptx -OutDir qa_images [-WidthPx 1400]
param(
    [Parameter(Mandatory = $true)][string]$Deck,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$WidthPx = 1400
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$Deck = (Resolve-Path $Deck).Path
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path

# --- Путь 1: PowerPoint COM ---
# Примечание: WithWindow=$false ряд сборок PowerPoint отклоняет
# («PowerPoint could not open the file»), поэтому окно открывается (msoTrue).
$ppt = $null
try { $ppt = New-Object -ComObject PowerPoint.Application } catch { $ppt = $null }
if ($ppt) {
    $pres = $null
    try {
        $pres = $ppt.Presentations.Open($Deck, $true, $false, $true)  # ReadOnly, не Untitled, с окном
        $n = $pres.Slides.Count
        $ratio = $pres.PageSetup.SlideHeight / $pres.PageSetup.SlideWidth
        $h = [int]($WidthPx * $ratio)
        foreach ($slide in $pres.Slides) {
            $num = "{0:D2}" -f $slide.SlideIndex
            $slide.Export((Join-Path $OutDir "slide-$num.png"), "PNG", $WidthPx, $h)
        }
        Write-Output "OK (PowerPoint): слайдов $n -> $OutDir"
        return
    } catch {
        Write-Warning "PowerPoint COM не сработал: $($_.Exception.Message)"
    } finally {
        if ($pres) { try { $pres.Close() } catch {} }
        try { $ppt.Quit() } catch {}
        [Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
    }
}

# --- Путь 2: LibreOffice -> PDF -> PNG ---
$soffice = $null
$cmd = Get-Command soffice -ErrorAction SilentlyContinue
if ($cmd) { $soffice = $cmd.Source }
if (-not $soffice) {
    foreach ($c in @("$env:ProgramFiles\LibreOffice\program\soffice.exe",
                     "${env:ProgramFiles(x86)}\LibreOffice\program\soffice.exe")) {
        if (Test-Path $c) { $soffice = $c; break }
    }
}
if ($soffice) {
    $tmpPdf = Join-Path $env:TEMP ([IO.Path]::GetFileNameWithoutExtension($Deck) + ".pdf")
    Remove-Item $tmpPdf -ErrorAction SilentlyContinue
    & $soffice --headless --convert-to pdf --outdir $env:TEMP $Deck | Out-Null
    if (Test-Path $tmpPdf) {
        $conv = Get-Command pdftoppm -ErrorAction SilentlyContinue
        if ($conv) {
            & pdftoppm -png -scale-to-x $WidthPx -scale-to-y -1 $tmpPdf (Join-Path $OutDir "slide")
            Remove-Item $tmpPdf -ErrorAction SilentlyContinue
            Write-Output "OK (LibreOffice): слайды -> $OutDir"
            return
        }
        Write-Output "PDF готов: $tmpPdf (для PNG установите poppler/pdftoppm или просмотрите PDF вручную)"
        return
    }
    Write-Warning "LibreOffice не сконвертировал файл в PDF"
}

Write-Error "Не найден ни PowerPoint, ни LibreOffice (либо оба не смогли открыть файл). Установите одно из них для визуального контроля, либо выполните текстовый QA: python scripts/extract_text.py <deck.pptx>"
exit 2
