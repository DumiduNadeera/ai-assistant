Add-Type -AssemblyName System.Drawing

$outputDir = Join-Path $PSScriptRoot '..\docs\diagrams'
[System.IO.Directory]::CreateDirectory($outputDir) | Out-Null
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $outputDir 'existing-langgraph.png'))

$width = 1800
$height = 1880
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$graphics.Clear([System.Drawing.Color]::FromArgb(248, 250, 252))

$titleFont = New-Object System.Drawing.Font('Segoe UI', 28, [System.Drawing.FontStyle]::Bold)
$nodeFont = New-Object System.Drawing.Font('Segoe UI', 15, [System.Drawing.FontStyle]::Bold)
$detailFont = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Regular)
$edgeFont = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(15, 23, 42))
$mutedBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(71, 85, 105))
$linePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(71, 85, 105), 3)
$linePen.CustomEndCap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(6, 7)
$dashPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(100, 116, 139), 2)
$dashPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
$dashPen.CustomEndCap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(5, 6)

function Draw-RoundNode([int]$x, [int]$y, [int]$w, [int]$h, [string]$title, [string]$detail, [System.Drawing.Color]$fill) {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $radius = 20
    $path.AddArc($x, $y, $radius, $radius, 180, 90)
    $path.AddArc($x + $w - $radius, $y, $radius, $radius, 270, 90)
    $path.AddArc($x + $w - $radius, $y + $h - $radius, $radius, $radius, 0, 90)
    $path.AddArc($x, $y + $h - $radius, $radius, $radius, 90, 90)
    $path.CloseFigure()
    $brush = New-Object System.Drawing.SolidBrush($fill)
    $border = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(148, 163, 184), 2)
    $graphics.FillPath($brush, $path)
    $graphics.DrawPath($border, $path)
    $titleSize = $graphics.MeasureString($title, $nodeFont)
    $graphics.DrawString($title, $nodeFont, $textBrush, $x + (($w - $titleSize.Width) / 2), $y + 15)
    if ($detail) {
        $format = New-Object System.Drawing.StringFormat
        $format.Alignment = [System.Drawing.StringAlignment]::Center
        $detailRect = [System.Drawing.RectangleF]::new([single]($x + 12), [single]($y + 50), [single]($w - 24), [single]($h - 55))
        $graphics.DrawString($detail, $detailFont, $mutedBrush, $detailRect, $format)
        $format.Dispose()
    }
    $brush.Dispose(); $border.Dispose(); $path.Dispose()
}

function Draw-Diamond([int]$cx, [int]$cy, [int]$w, [int]$h, [string]$label) {
    $halfW = [int]($w / 2)
    $halfH = [int]($h / 2)
    [System.Drawing.Point[]]$points = @(
        [System.Drawing.Point]::new($cx, ($cy - $halfH)),
        [System.Drawing.Point]::new(($cx + $halfW), $cy),
        [System.Drawing.Point]::new($cx, ($cy + $halfH)),
        [System.Drawing.Point]::new(($cx - $halfW), $cy)
    )
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(254, 240, 138))
    $border = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(161, 98, 7), 2)
    $graphics.FillPolygon($brush, $points)
    $graphics.DrawPolygon($border, $points)
    $size = $graphics.MeasureString($label, $nodeFont)
    $graphics.DrawString($label, $nodeFont, $textBrush, $cx - ($size.Width/2), $cy - ($size.Height/2))
    $brush.Dispose(); $border.Dispose()
}

function Draw-Arrow([int]$x1, [int]$y1, [int]$x2, [int]$y2, [string]$label = '') {
    $graphics.DrawLine($linePen, $x1, $y1, $x2, $y2)
    if ($label) {
        $size = $graphics.MeasureString($label, $edgeFont)
        $graphics.DrawString($label, $edgeFont, $mutedBrush, (($x1 + $x2 - $size.Width) / 2), (($y1 + $y2 - $size.Height) / 2) - 8)
    }
}

$graphics.DrawString('Enterprise AI Assistant — Compiled LangGraph', $titleFont, $textBrush, 480, 30)
$graphics.DrawString('Typed orchestration with policy, retrieval, research, tools, validation, and memory', $detailFont, $mutedBrush, 585, 80)

Draw-RoundNode 750 120 300 70 'START' '' ([System.Drawing.Color]::FromArgb(226, 232, 240))
Draw-RoundNode 700 225 400 100 'validate_request' 'Input validation and prompt-injection policy' ([System.Drawing.Color]::FromArgb(219, 234, 254))
Draw-RoundNode 700 365 400 100 'load_memory' 'Load owned, bounded conversation history' ([System.Drawing.Color]::FromArgb(219, 234, 254))
Draw-RoundNode 700 505 400 100 'supervisor_agent' 'Classify intent, complexity, route, and tool request' ([System.Drawing.Color]::FromArgb(219, 234, 254))
Draw-Diamond 900 710 350 150 'Selected route'

Draw-RoundNode 80 850 390 110 'retrieval_agent' 'Authorized knowledge search; dense + BM25 fusion' ([System.Drawing.Color]::FromArgb(220, 252, 231))
Draw-RoundNode 510 850 390 110 'research_planner' 'Create bounded targeted subqueries' ([System.Drawing.Color]::FromArgb(220, 252, 231))
Draw-RoundNode 510 1010 390 110 'research_agent' 'Bounded recursive retrieval, evidence refinement, aggregation' ([System.Drawing.Color]::FromArgb(220, 252, 231))

Draw-RoundNode 1020 850 390 110 'authorize_tool' 'Deterministic role and tool policy check' ([System.Drawing.Color]::FromArgb(243, 232, 255))
Draw-Diamond 1215 1060 315 140 'Authorized?'
Draw-RoundNode 1020 1190 390 110 'enterprise_tool' 'Invoke read-only MCP client with a deadline' ([System.Drawing.Color]::FromArgb(243, 232, 255))

Draw-RoundNode 270 1190 420 110 'validate_evidence' 'Metadata, ACL, content, and source validation' ([System.Drawing.Color]::FromArgb(255, 237, 213))
Draw-RoundNode 700 1360 400 110 'response_agent' 'Grounded synthesis or safe denial / degradation' ([System.Drawing.Color]::FromArgb(220, 252, 231))
Draw-RoundNode 700 1510 400 100 'validate_response' 'Schema and citation identity validation' ([System.Drawing.Color]::FromArgb(255, 237, 213))
Draw-RoundNode 700 1650 400 100 'save_memory' 'Persist the bounded user and assistant turn' ([System.Drawing.Color]::FromArgb(219, 234, 254))
Draw-RoundNode 750 1790 300 60 'END' '' ([System.Drawing.Color]::FromArgb(226, 232, 240))

Draw-Arrow 900 190 900 225
Draw-Arrow 900 325 900 365
Draw-Arrow 900 465 900 505
Draw-Arrow 900 605 900 635
Draw-Arrow 775 775 360 850 'retrieval'
Draw-Arrow 850 785 705 850 'research'
Draw-Arrow 1025 785 1150 850 'tool'
Draw-Arrow 1070 750 1080 1360 'denied'
Draw-Arrow 275 960 430 1190
Draw-Arrow 705 960 705 1010
Draw-Arrow 610 1120 570 1190
Draw-Arrow 1215 960 1215 990
Draw-Arrow 1125 1115 1125 1190 'yes'
Draw-Arrow 1350 1085 1100 1390 'no'
Draw-Arrow 480 1300 790 1360
Draw-Arrow 1215 1300 1010 1360
Draw-Arrow 900 1470 900 1510
Draw-Arrow 900 1610 900 1650
Draw-Arrow 900 1750 900 1790

$bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)

$dashPen.Dispose(); $linePen.Dispose(); $mutedBrush.Dispose(); $textBrush.Dispose()
$edgeFont.Dispose(); $detailFont.Dispose(); $nodeFont.Dispose(); $titleFont.Dispose()
$graphics.Dispose(); $bitmap.Dispose()

Write-Output $outputPath
