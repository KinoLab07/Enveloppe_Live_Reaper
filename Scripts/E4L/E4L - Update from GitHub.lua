-- E4L - Update from GitHub.lua
-- Envelop for REAPER: downloads the latest version of the project from GitHub (branch main)
-- and copies it into REAPER's resource folder:
--   Effects/E4L  (plugins)   Data/E4L  (HRTF filters, guide)   Scripts/E4L  (scripts)
-- Only these three E4L folders are touched. macOS and Linux use curl + unzip, Windows uses
-- PowerShell. The download runs in the background: REAPER stays responsive and a small
-- window shows the progress. GPLv2 or later (same as Envelop for Live).

local REPO   = "KinoLab07/enveloppe_live_reaper"
local BRANCH = "main"
local ZIP    = "https://github.com/" .. REPO .. "/archive/refs/heads/" .. BRANCH .. ".zip"
local API    = "https://api.github.com/repos/" .. REPO .. "/commits/" .. BRANCH
local EXT    = "E4L_Update"
local TIMEOUT = 240          -- seconds before giving up on a step

local function msg(s) reaper.ShowMessageBox(s, "E4L - Update", 0) end

local is_win = reaper.GetOS():match("^Win") ~= nil
local res = reaper.GetResourcePath()
local sep = is_win and "\\" or "/"
local tmp = (os.getenv(is_win and "TEMP" or "TMPDIR") or (is_win and "C:\\Windows\\Temp" or "/tmp"))
tmp = tmp:gsub("[/\\]$", "") .. sep .. "e4l_update"

local function read_file(p)
  local f = io.open(p, "r"); if not f then return nil end
  local s = f:read("*a"); f:close(); return s
end

local function write_file(p, s)
  local f = io.open(p, "w"); if not f then return false end
  f:write(s); f:close(); return true
end

---------------------------------------------------------------------------------------------
-- Progress window
---------------------------------------------------------------------------------------------
local win_open, status_text, t_start = false, "", 0

local function win_draw()
  if not win_open then return end
  if gfx.getchar() < 0 then win_open = false; return end      -- closed by the user
  gfx.set(0.12, 0.12, 0.14, 1); gfx.rect(0, 0, gfx.w, gfx.h, 1)
  gfx.setfont(1, "Arial", 16)
  gfx.set(0.9, 0.9, 0.9, 1); gfx.x, gfx.y = 16, 16; gfx.drawstr(status_text)
  local dots = math.floor((reaper.time_precise() - t_start) * 3) % 4
  gfx.setfont(1, "Arial", 13)
  gfx.set(0.6, 0.6, 0.6, 1); gfx.x, gfx.y = 16, 44
  gfx.drawstr(string.format("%d s%s   (REAPER keeps working)",
              math.floor(reaper.time_precise() - t_start), string.rep(".", dots)))
  gfx.update()
end

local function win_show(text)
  status_text = text
  if not win_open then
    gfx.init("E4L - Update", 380, 76)
    win_open = true
  end
end

local function win_close()
  if win_open then gfx.quit(); win_open = false end
end

---------------------------------------------------------------------------------------------
-- Runs a shell / PowerShell script in the background and calls done(output) when it ends.
-- REAPER is never blocked: we poll for a "done" file with defer.
---------------------------------------------------------------------------------------------
local job = 0
local function run_async(text, script_text, done)
  job = job + 1
  local base = tmp .. "_job" .. job
  local work, log, flag = base .. (is_win and ".ps1" or ".sh"), base .. ".log", base .. ".done"
  os.remove(log); os.remove(flag)
  local ok
  if is_win then
    ok = write_file(work,
      '$ProgressPreference = "SilentlyContinue"\n' ..
      'try { & {\n' .. script_text .. '\n} *>&1 | Out-File -Encoding ascii "' .. log .. '" }\n' ..
      'catch { $_ | Out-File -Append -Encoding ascii "' .. log .. '" }\n' ..
      '"done" | Out-File -Encoding ascii "' .. flag .. '"\n')
  else
    ok = write_file(work, script_text) and write_file(base .. "_launch.sh",
      '( /bin/sh "' .. work .. '" > "' .. log .. '" 2>&1; echo "$?" > "' .. flag .. '" ) ' ..
      '< /dev/null > /dev/null 2>&1 &\n')
  end
  if not ok then done(nil, "Cannot write to " .. base); return end

  if is_win then
    reaper.ExecProcess('powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' ..
                       work .. '"', -2)                      -- -2 = do not wait
  else
    reaper.ExecProcess('/bin/sh "' .. base .. '_launch.sh"', 10000)   -- returns at once
  end

  win_show(text)
  t_start = reaper.time_precise()
  local function poll()
    if read_file(flag) then
      local out = read_file(log) or ""
      for _, p in ipairs({ work, log, flag, base .. "_launch.sh" }) do os.remove(p) end
      done(out)
      return
    end
    if reaper.time_precise() - t_start > TIMEOUT then
      done(nil, "No answer after " .. TIMEOUT .. " seconds (" .. (read_file(log) or "") .. ")")
      return
    end
    win_draw()
    reaper.defer(poll)
  end
  reaper.defer(poll)
end

---------------------------------------------------------------------------------------------
-- After a successful update
---------------------------------------------------------------------------------------------
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

-- puts every "E4L - ….lua" action script in REAPER's action list (new ones appear without
-- having to load them by hand; already registered ones are left as they are)
local function register_actions()
  local dir = res .. sep .. "Scripts" .. sep .. "E4L"
  local files, i = {}, 0
  while true do
    local f = reaper.EnumerateFiles(dir, i)
    if not f then break end
    if f:match("^E4L %- .+%.lua$") then files[#files + 1] = f end
    i = i + 1
  end
  local n = 0
  for k, f in ipairs(files) do
    if reaper.AddRemoveReaScript(true, 0, dir .. sep .. f, k == #files) ~= 0 then n = n + 1 end
  end
  return n
end

local function finished(sha, out, err)
  win_close()
  if out and out:find("E4L_OK", 1, true) then
    if sha then reaper.SetExtState(EXT, "sha", sha, true) end
    local n_actions = register_actions()
    -- close the running Live Panel (it reopens with the new version)
    local alive = tonumber(reaper.GetExtState("E4L_LivePanel", "alive")) or 0
    local panel_open = reaper.time_precise() - alive < 1.5
    if panel_open then reaper.SetExtState("E4L_LivePanel", "quit", "1", false) end
    msg("E4L updated" .. (sha and (" (version " .. sha:sub(1, 7) .. ")") or "") .. ".\n\n" ..
        "• " .. n_actions .. " E4L scripts are in the action list (Actions > Show action list, search E4L).\n" ..
        "• The PDF guide is in: " .. res .. sep .. "Data" .. sep .. "E4L" ..
        (panel_open and "\n• The Live Panel reopens with the new version." or ""))
    reopen_project_and_panel(panel_open)
  else
    msg("The update failed.\n\nCheck the internet connection and try again.\n\n" ..
        "Details:\n" .. tostring(err or out or "no answer"):sub(1, 600))
  end
end

---------------------------------------------------------------------------------------------
-- 2. download, unzip and copy
---------------------------------------------------------------------------------------------
local function install(sha)
  local script
  if is_win then
    script = table.concat({
      '$ErrorActionPreference = "Stop"',
      '$tmp = "' .. tmp .. '"', '$res = "' .. res .. '"',
      'if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }',
      'New-Item -ItemType Directory -Force $tmp | Out-Null',
      'Invoke-WebRequest -TimeoutSec 180 -Uri "' .. ZIP .. '" -OutFile "$tmp\\e4l.zip"',
      'Expand-Archive -Path "$tmp\\e4l.zip" -DestinationPath $tmp -Force',
      '$src = Get-ChildItem -Directory $tmp | Select-Object -First 1',
      'foreach ($d in @("Effects\\E4L", "Data\\E4L", "Scripts\\E4L")) {',
      '  New-Item -ItemType Directory -Force "$res\\$d" | Out-Null',
      '  Copy-Item -Recurse -Force "$($src.FullName)\\$d\\*" "$res\\$d\\"',
      '}',
      'Copy-Item -Force "$($src.FullName)\\docs\\*.pdf" "$res\\Data\\E4L\\"',
      'Remove-Item -Recurse -Force $tmp',
      'Write-Output "E4L_OK"',
    }, "\n")
  else
    script = table.concat({
      'set -e',
      'TMP="' .. tmp .. '"', 'RES="' .. res .. '"',
      'rm -rf "$TMP"; mkdir -p "$TMP"',
      'curl -fsSL --connect-timeout 20 --max-time 180 -o "$TMP/e4l.zip" "' .. ZIP .. '"',
      'unzip -q -o "$TMP/e4l.zip" -d "$TMP"',
      'SRC=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)',
      'for d in Effects/E4L Data/E4L Scripts/E4L; do',
      '  mkdir -p "$RES/$d"',
      '  cp -R "$SRC/$d/." "$RES/$d/"',
      'done',
      'cp "$SRC"/docs/*.pdf "$RES/Data/E4L/" 2>/dev/null || true',
      'rm -rf "$TMP"',
      'echo E4L_OK',
    }, "\n") .. "\n"
  end
  run_async("Downloading and installing E4L...", script, function(out, err)
    finished(sha, out, err)
  end)
end

---------------------------------------------------------------------------------------------
-- 1. latest commit on GitHub (to tell whether there is something new)
---------------------------------------------------------------------------------------------
local script
if is_win then
  script = '(Invoke-RestMethod -TimeoutSec 20 -Uri "' .. API ..
           '" -Headers @{ "User-Agent" = "E4L" }).sha'
else
  script = 'curl -fsSL --connect-timeout 10 --max-time 20 -H "User-Agent: E4L" "' .. API ..
           '" | grep -m1 \'"sha"\'\n'
end
run_async("Checking GitHub for a new version...", script, function(out)
  local sha = out and out:match(string.rep("%x", 40))
  local installed = reaper.GetExtState(EXT, "sha")
  if sha and sha == installed then
    win_close()
    local r = reaper.ShowMessageBox("You already have the latest version (" .. sha:sub(1, 7) .. ").\n\n" ..
                                    "Reinstall anyway?", "E4L - Update", 4)
    if r ~= 6 then return end
  end
  install(sha)        -- if GitHub could not be asked (sha = nil) we just download
end)
