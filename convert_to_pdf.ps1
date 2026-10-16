param (
    [string]$DocxPath = "Paper_CV.docx",
    [string]$PdfPath = "Paper_CV.pdf"
)

$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
    $docxFull = (Resolve-Path $DocxPath).Path
    $pdfFull = [System.IO.Path]::GetFullPath($PdfPath)
    Write-Host "Opening: $docxFull"
    $d = $w.Documents.Open($docxFull, $false, $true)
    Write-Host "Saving PDF to: $pdfFull"
    $d.ExportAsFixedFormat($pdfFull, 17)
    $pages = $d.ComputeStatistics(2)
    Write-Host "Total Pages: $pages"
    $d.Close(0)
    Write-Host "Successfully generated PDF with $pages pages."
} finally {
    $w.Quit()
}
