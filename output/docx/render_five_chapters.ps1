$reportPath = 'C:\Users\ACER\Desktop\Projects\Aphrodize\output\docx\aphrodize_report_5_chapters.docx'
$qaPdfPath = 'C:\Users\ACER\Desktop\Projects\Aphrodize\output\docx\qa-five-chapters\report.pdf'
$wordApp = $null
$reportDoc = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $reportDoc = $wordApp.Documents.Open($reportPath, $false, $true)
    $reportDoc.Repaginate()
    $reportDoc.ExportAsFixedFormat($qaPdfPath, 17)
    Write-Output "Rendered pages: $($reportDoc.ComputeStatistics(2))"
} finally {
    if ($null -ne $reportDoc) { $reportDoc.Close(0) }
    if ($null -ne $wordApp) { $wordApp.Quit() }
}
