-- E4L - Update from GitHub.lua
-- Envelop for REAPER: downloads the latest version of the project from GitHub (branch main)
-- and copies it into REAPER's resource folder:
--   Effects/E4L  (plugins)   Data/E4L  (HRTF filters, guide)   Scripts/E4L  (scripts)
-- Only these three E4L folders are touched. macOS and Linux use curl + unzip, Windows uses
-- PowerShell. GPLv2 or later (same as Envelop for Live).

local REPO   = "KinoLab07/enveloppe_live_reaper"
local BRANCH = "main"
local ZIP    = "https://github.com/" .. REPO .. "/archive/refs/heads/" .. BRANCH .. ".zip"
local API    = "https://api.github.com/repos/" .. REPO .. "/commits/" .. BRANCH
local EXT    = "E4L_Update"

local function msg(s) reaper.ShowMessageBox(s, "E4L - Actualizar", 0) end

local is_win = reaper.GetOS():match("^Win") ~= nil
local res = reaper.GetResourcePath()
local sep = is_win and "\\" or "/"
local tmp = (os.getenv(is_win and "TEMP" or "TMPDIR") or (is_win and "C:\\Windows\\Temp" or "/tmp"))
tmp = tmp:gsub("[/\\]$", "") .. sep .. "e4l_update"

local function run(script_text)
  -- writes a small shell / PowerShell script and runs it; returns its output
  local path = tmp .. (is_win and "_run.ps1" or "_run.sh")
  local f = io.open(path, "w")
  if not f then return nil, "No se puede escribir en " .. path end
  f:write(script_text); f:close()
  local cmd = is_win and ('powershell -NoProfile -ExecutionPolicy Bypass -File "' .. path .. '"')
                      or ('/bin/sh "' .. path .. '"')
  local out = reaper.ExecProcess(cmd, 180000)
  os.remove(path)
  return out
end

-- 1. latest commit on GitHub (to tell whether there is something new)
local function latest_sha()
  local out
  if is_win then
    out = run('$ProgressPreference = "SilentlyContinue"\n' ..
              '(Invoke-RestMethod -Uri "' .. API .. '" -Headers @{ "User-Agent" = "E4L" }).sha\n')
  else
    out = run('curl -fsSL -H "User-Agent: E4L" "' .. API .. '" | grep -m1 \'"sha"\'\n')
  end
  return out and out:match("(%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x)")
end

local sha = latest_sha()
local installed = reaper.GetExtState(EXT, "sha")
if sha and sha == installed then
  local r = reaper.ShowMessageBox("Ya tienes la última versión (" .. sha:sub(1, 7) .. ").\n\n" ..
                                  "¿Reinstalar igualmente?", "E4L - Actualizar", 4)
  if r ~= 6 then return end
end

-- 2. download, unzip and copy
local out
if is_win then
  out = run(table.concat({
    '$ErrorActionPreference = "Stop"', '$ProgressPreference = "SilentlyContinue"',
    '$tmp = "' .. tmp .. '"', '$res = "' .. res .. '"',
    'if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }',
    'New-Item -ItemType Directory -Force $tmp | Out-Null',
    'Invoke-WebRequest -Uri "' .. ZIP .. '" -OutFile "$tmp\\e4l.zip"',
    'Expand-Archive -Path "$tmp\\e4l.zip" -DestinationPath $tmp -Force',
    '$src = Get-ChildItem -Directory $tmp | Select-Object -First 1',
    'foreach ($d in @("Effects\\E4L", "Data\\E4L", "Scripts\\E4L")) {',
    '  New-Item -ItemType Directory -Force "$res\\$d" | Out-Null',
    '  Copy-Item -Recurse -Force "$($src.FullName)\\$d\\*" "$res\\$d\\"',
    '}',
    'Copy-Item -Force "$($src.FullName)\\docs\\Guia_E4L_REAPER_Cuadrafonia.pdf" "$res\\Data\\E4L\\"',
    'Remove-Item -Recurse -Force $tmp',
    'Write-Output "E4L_OK"',
  }, "\n") .. "\n")
else
  out = run(table.concat({
    'set -e',
    'TMP="' .. tmp .. '"', 'RES="' .. res .. '"',
    'rm -rf "$TMP"; mkdir -p "$TMP"',
    'curl -fsSL -o "$TMP/e4l.zip" "' .. ZIP .. '"',
    'unzip -q -o "$TMP/e4l.zip" -d "$TMP"',
    'SRC=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)',
    'for d in Effects/E4L Data/E4L Scripts/E4L; do',
    '  mkdir -p "$RES/$d"',
    '  cp -R "$SRC/$d/." "$RES/$d/"',
    'done',
    'cp "$SRC/docs/Guia_E4L_REAPER_Cuadrafonia.pdf" "$RES/Data/E4L/" 2>/dev/null || true',
    'rm -rf "$TMP"',
    'echo E4L_OK',
  }, "\n") .. "\n")
end

if out and out:find("E4L_OK", 1, true) then
  if sha then reaper.SetExtState(EXT, "sha", sha, true) end
  msg("E4L actualizado" .. (sha and (" (versión " .. sha:sub(1, 7) .. ")") or "") .. ".\n\n" ..
      "• Plugins: pulsa F5 en el navegador de FX. Los que ya están en un proyecto se\n" ..
      "  actualizan al volver a abrir el proyecto.\n" ..
      "• Si el E4L Live Panel está abierto, ciérralo y vuelve a lanzarlo.\n" ..
      "• La guía en PDF quedó en: " .. res .. sep .. "Data" .. sep .. "E4L")
else
  msg("No se pudo actualizar.\n\nComprueba la conexión a internet y vuelve a intentarlo.\n\n" ..
      "Detalle:\n" .. tostring(out or "sin respuesta"):sub(1, 600))
end
