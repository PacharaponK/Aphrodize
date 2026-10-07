$ErrorActionPreference = 'Stop'
$reportPath = 'C:\Users\ACER\Desktop\Projects\Aphrodize\output\docx\Aphrodize_Report_5_Chapters.docx'
$qaPdfPath = 'C:\Users\ACER\Desktop\Projects\Aphrodize\output\docx\qa-components\report.pdf'
$wordApp = $null
$reportDoc = $null
try {
    Write-Output 'Starting background Word'
    $wordApp = New-Object -ComObject Word.Application
    Write-Output 'Word application created'
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $reportDoc = $wordApp.Documents.Open($reportPath, $false, $true)
    Write-Output 'Report opened'
    $reportDoc.Repaginate()
    $reportDoc.ExportAsFixedFormat($qaPdfPath, 17)
    Write-Output "Rendered pages: $($reportDoc.ComputeStatistics(2))"
} finally {
    if ($null -ne $reportDoc) { $reportDoc.Close(0) }
    if ($null -ne $wordApp) { $wordApp.Quit() }
}
