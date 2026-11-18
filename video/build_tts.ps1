# Genera la VOZ GUIA (voz sintetica de Windows) para cada escena del video.
# Sirve solo para medir tiempos y armar la linea de tiempo; despues cada
# integrante graba su voz real y reemplaza estos archivos en DaVinci Resolve.
#   powershell -ExecutionPolicy Bypass -File video\build_tts.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $here "tts"
New-Item -ItemType Directory -Force $out | Out-Null
Add-Type -AssemblyName System.Speech
$json = Get-Content (Join-Path $here "guion_video.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(48000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)

function Save-Voice([string]$text, [string]$file) {
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.SelectVoice("Microsoft Helena Desktop")
    $s.Rate = 1
    $s.SetOutputToWaveFile($file, $fmt)
    $s.Speak($text)
    $s.Dispose()
}

foreach ($e in $json.escenas) {
    if ($e.lineas) {
        $i = 0
        foreach ($l in $e.lineas) { $i++; Save-Voice $l.texto (Join-Path $out ("{0}_{1:D2}_{2}.wav" -f $e.id, $i, $l.evento)) }
    } elseif ($e.texto) {
        Save-Voice $e.texto (Join-Path $out "$($e.id).wav")
    }
}
Get-ChildItem $out -Filter *.wav | ForEach-Object {
    $d = & ffprobe -v error -show_entries format=duration -of csv=p=0 $_.FullName
    "{0}`t{1:N2}" -f $_.BaseName, [double]$d
} | Out-File -Encoding utf8 (Join-Path $out "duraciones.tsv")
