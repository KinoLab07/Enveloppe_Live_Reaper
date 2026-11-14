-- e4l_control.lua  (not an action: shared code of the "E4L ctl - …" control actions)
-- Envelop for REAPER. GPLv2 or later (same as Envelop for Live).
--
-- Every "E4L ctl - <TARGET> <ACTION>.lua" in Scripts/E4L/Controls is one button of the Live
-- Panel as a REAPER action, so it can be bound to a MIDI note / CC / pad: Actions > Show action
-- list > select it > Add… (shortcut) > press the button of the controller.
--   LOOP n   REC | PLAY | PAUSE | OVERDUB | CLEAR
--   AUDIO n  PLAY | PAUSE
--   LIVE n   ON-OFF
--   MASTER   PLAY-STOP | PAUSE | REC SESSION | STOP ALL LOOPS | REC START
-- When the Live Panel is open the command goes through it (exactly like a click: audio files
-- quantised to the bar, status line...). When it is closed, loops, live inputs and the
-- transport are driven directly; the other commands need the panel.
-- A MIDI button that also sends a "release" (value 0) is ignored on release, so a button
-- toggles once per press.

local E4L = dofile((debug.getinfo(1, "S").source:match("@?(.*[/\\])") or "") .. "e4l_lib.lua")

local M = {}
M.EXT = "E4L_LivePanel"

function M.parse(file)
  local name = (file or ""):match("([^/\\]+)%.lua$") or ""
  local body = name:match("^E4L ctl %- (.+)$")
  if not body then return end
  local target, action = body:match("^(LOOP %d+) (.+)$")
  if not target then target, action = body:match("^(AUDIO %d+) (.+)$") end
  if not target then target, action = body:match("^(LIVE %d+) (.+)$") end
  if not target then target, action = body:match("^(MASTER) (.+)$") end
  return target, action
end

function M.panel_alive()
  local alive = tonumber(reaper.GetExtState(M.EXT, "alive")) or 0
  return reaper.time_precise() - alive < 1.5
end

-- the panel takes the queued commands one by one ("TARGET|ACTION" lines)
function M.queue(target, action)
  local q = reaper.GetExtState(M.EXT, "cmds")
  reaper.SetExtState(M.EXT, "cmds", q .. target .. "|" .. action .. "\n", false)
end

function M.take_queue()
  local q = reaper.GetExtState(M.EXT, "cmds")
  if q == "" then return {} end
  reaper.SetExtState(M.EXT, "cmds", "", false)
  local t = {}
  for line in q:gmatch("[^\n]+") do
    local target, action = line:match("^(.-)|(.+)$")
    if target then t[#t + 1] = { target, action } end
  end
  return t
end

-- a JSFX slider by name on the first FX whose name contains `fxname`
local function param(tr, fxname, pname)
  local fx = E4L.find_fx(tr, fxname)
  if fx < 0 then return end
  for p = 0, reaper.TrackFX_GetNumParams(tr, fx) - 1 do
    local _, n = reaper.TrackFX_GetParamName(tr, fx, p, "")
    if n == pname then return fx, p end
  end
end

local function toggle(tr, pname)
  local fx, p = param(tr, "E4L Looper", pname)
  if fx then reaper.TrackFX_SetParam(tr, fx, p, reaper.TrackFX_GetParam(tr, fx, p) > 0.5 and 0 or 1) end
end

-- without the panel: what can be done directly
function M.direct(target, action)
  local tr = target ~= "MASTER" and E4L.find_track(target)
  if target:match("^LOOP") and tr then
    if action == "REC" then toggle(tr, "Record")
    elseif action == "PLAY" then toggle(tr, "Play")
    elseif action == "PAUSE" then toggle(tr, "Pause")
    elseif action == "OVERDUB" then toggle(tr, "Overdub")
    elseif action == "CLEAR" then
      local fx, p = param(tr, "E4L Looper", "Clear")
      if fx then reaper.TrackFX_SetParam(tr, fx, p, 1) end
    end
    return true
  elseif target:match("^LIVE") and tr then
    reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") > 0.5 and 0 or 1)
    return true
  elseif target == "MASTER" and action == "PLAY-STOP" then
    if reaper.GetPlayState() % 2 == 1 then reaper.OnStopButton(); reaper.SetEditCurPos(0, true, false)
    else reaper.OnPlayButton() end
    return true
  elseif target == "MASTER" and action == "PAUSE" then
    reaper.OnPauseButton()
    return true
  end
  return false
end

-- run by each "E4L ctl - …" action
function M.run(file)
  local _, ctx_file, _, _, _, _, val = reaper.get_action_context()
  if val == 0 then return end                         -- MIDI button released
  local target, action = M.parse(file or ctx_file)
  if not target then return end
  if M.panel_alive() then M.queue(target, action)
  elseif not M.direct(target, action) then
    E4L.msg("Open the Live Panel to use \"" .. target .. " " .. action .. "\" from MIDI.", "E4L")
  end
end

return M
