param([Parameter(Mandatory=$true)][string]$ImagePath,[Parameter(Mandatory=$true)][string]$Languages)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
    $null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
    $null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
    $null=[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
    $asTask=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1} | Select-Object -First 1
    function Await($operation,$type) {
        $task=$asTask.MakeGenericMethod($type).Invoke($null,@($operation))
        $task.GetAwaiter().GetResult()
    }
    $file=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])
    $stream=Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    try {
        $decoder=Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap=Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        try {
            $results=[System.Collections.Generic.List[string]]::new()
            foreach ($tag in $Languages.Split('+')) {
                $engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($tag))
                if ($null -eq $engine) { continue }
                $result=Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
                if ($result.Text) {$results.Add($result.Text)}
            }
            if ($results.Count -eq 0) {
                # Distinguish an unavailable language from a legitimately blank scan.
                $available=@([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object {$_.LanguageTag})
                $usable=@($Languages.Split('+') | Where-Object {[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($_))})
                if ($usable.Count -eq 0) { [Console]::Error.WriteLine('OCR language unavailable. Enable an OCR language in Windows Settings.'); exit 3 }
            }
            [Console]::Write(($results | Select-Object -Unique) -join "`n")
        } finally {$bitmap.Dispose()}
    } finally {$stream.Dispose()}
    exit 0
} catch {
    [Console]::Error.WriteLine('Windows OCR failed. Check image format and installed OCR languages.')
    exit 1
}
