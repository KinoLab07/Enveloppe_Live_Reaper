-- E4L - Nuevo proyecto en vivo.lua
-- Envelop for REAPER: one click to start playing.
--   1. new project (REAPER asks to save the current one if it has changes)
--   2. "E4L - Live Looper template": SYNTH IN, LOOP tracks, E4L Master (quad), CUE, sub
--   3. "E4L - Live Panel" (only if it is not already open)
-- GPLv2 or later (same as Envelop for Live).

local DIR = debug.getinfo(1, "S").source:match("@?(.*[/\\])") or ""
local E4L = dofile(DIR .. "e4l_lib.lua")

reaper.Main_OnCommand(40023, 0)                      -- File: New project

-- the template is only needed if the project does not have it yet (the new project may come
-- from a default template that already has it, or the user may have cancelled)
if not E4L.find_track("E4L Master") then
  dofile(DIR .. "E4L - Live Looper template.lua")
end

local alive = tonumber(reaper.GetExtState("E4L_LivePanel", "alive")) or 0
if reaper.time_precise() - alive > 1.5 then
  dofile(DIR .. "E4L - Live Panel.lua")
end
