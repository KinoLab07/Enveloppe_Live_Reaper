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

local function msg(s) reaper.ShowMessageBox(s, "E4L - Update", 0) end

local is_win = reaper.GetOS():match("^Win") ~= nil
local res = reaper.GetResourcePath()
local sep = is_win and "\\" or "/"
local tmp = (os.getenv(is_win and "TEMP" or "TMPDIR") or (is_win and "C:\\Windows\\Temp" or "/tmp"))
tmp = tmp:gsub("[/\\]$", "") .. sep .. "e4l_update"

local function run(script_text)
  -- writes a small shell / PowerShell script and runs it; returns its output
  local path = tmp .. (is_win and "_run.ps1" or "_run.sh")
  local f = io.open(path, "w")
  if not f then return nil, "Cannot write to " .. path end
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
  local r = reaper.ShowMessageBox("You already have the latest version (" .. sha:sub(1, 7) .. ").\n\n" ..
                                  "Reinstall anyway?", "E4L - Update", 4)
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
    'Copy-Item -Force "$($src.FullName)\\docs\\*.pdf" "$res\\Data\\E4L\\"',
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
    'cp "$SRC"/docs/*.pdf "$RES/Data/E4L/" 2>/dev/null || true',
    'rm -rf "$TMP"',
    'echo E4L_OK',
  }, "\n") .. "\n")
end

local function reopen_project_and_panel(panel_was_open)
  -- 1. plugins: they are reloaded when the project is opened again
  local _, path = reaper.EnumProjects(-1, "")
  if path and path ~= "" then
    local r = reaper.ShowMessageBox(
      "Reopen the project to load the new plug-ins?\n\n" ..
      "(REAPER asks first if it has unsaved changes. Loops recorded in memory are lost.)",
      "E4L - Update", 4)
    if r == 6 then reaper.Main_openProject(path) end
  end
  -- 2. the panel: open the new version
  if panel_was_open then
    local f = res .. sep .. "Scripts" .. sep .. "E4L" .. sep .. "E4L - Live Panel.lua"
    local t0 = reaper.time_precise()
    local function wait()   -- give the old panel a moment to close
      if reaper.time_precise() - t0 < 0.6 then reaper.defer(wait) return end
      dofile(f)
    end
    wait()
  end
end

if out and out:find("E4L_OK", 1, true) then
  if sha then reaper.SetExtState(EXT, "sha", sha, true) end
  -- close the running Live Panel (it reopens with the new version)
  local alive = tonumber(reaper.GetExtState("E4L_LivePanel", "alive")) or 0
  local panel_open = reaper.time_precise() - alive < 1.5
  if panel_open then reaper.SetExtState("E4L_LivePanel", "quit", "1", false) end
  msg("E4L updated" .. (sha and (" (version " .. sha:sub(1, 7) .. ")") or "") .. ".\n\n" ..
      "• The PDF guide is in: " .. res .. sep .. "Data" .. sep .. "E4L" ..
      (panel_open and "\n• The Live Panel reopens with the new version." or ""))
  reopen_project_and_panel(panel_open)
else
  msg("The update failed.\n\nCheck the internet connection and try again.\n\n" ..
      "Details:\n" .. tostring(out or "no answer"):sub(1, 600))
end
