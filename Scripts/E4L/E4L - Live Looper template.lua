-- E4L - Live Looper template.lua
-- Envelop for REAPER: builds an Ableton-style live looping set-up for an analog synth,
-- spatialised in quadraphony with the E4L plugins.
--
--   SYNTH IN          audio input of the synth. Always to the headphones, never to the speakers.
--   LOOP 1..N         E4L Looper + E4L panner. Records N bars from the synth on the next bar
--                     and plays the loop in sync, spatialised, to "E4L Master".
--   E4L Master        E4L Master Bus = Quad -> REAPER master -> outputs 1-4.
--   MASTER            "E4L Sub Out": the sum of everything on the master -> sub output.
--   CUE (headphones)  binaural copy of the loops, to the headphone outputs.
--
-- Headphones: choose an output pair that is not a speaker, e.g. 7-8 on an Mbox Pro, and in the
-- interface's control panel set the headphone output source to that pair.
--
-- Running it again on a project that already has the template adds more LOOP tracks.
-- GPLv2 or later (same as Envelop for Live).

local DIR = debug.getinfo(1, "S").source:match("@?(.*[/\\])") or ""
local E4L = dofile(DIR .. "e4l_lib.lua")
local NCH = E4L.NCH
local function msg(s) E4L.msg(s, "E4L Live Looper") end
local find_track, new_track, add_fx, find_fx = E4L.find_track, E4L.new_track, E4L.add_fx, E4L.find_fx
local set_param, add_send, add_hw_out = E4L.set_param, E4L.add_send, E4L.add_hw_out

---------------------------------------------------------------------------------------
local existing = find_track("SYNTH IN")
local defaults = existing and "4,1,1,7,1,5" or "8,1,1,7,1,5"
local ok, csv = reaper.GetUserInputs("E4L Live Looper", 6,
  "Loop tracks to add,Synth input (first channel),Synth input: 1 mono 2 stereo," ..
  "Headphones output (first channel),Loop panner: 1 Mono 2 Stereo,Sub output (0 = none)", defaults)
if not ok then return end
local f = {}
for v in csv:gmatch("[^,]+") do f[#f + 1] = tonumber(v) end
local n_loops   = math.max(1, math.min(32, f[1] or 8))
local in_ch     = math.max(1, f[2] or 1)
local in_stereo = (f[3] or 1) == 2
local cue_ch    = math.max(1, f[4] or 7)
local stereo_pan = (f[5] or 1) == 2
local sub_ch    = math.max(0, f[6] or 0)

local lat_ms = E4L.latency_ms()
E4L.cfg_set("cue_ch", cue_ch); E4L.cfg_set("sub_ch", sub_ch)
E4L.cfg_set("stereo_pan", stereo_pan and 1 or 0); E4L.cfg_set("lat_ms", lat_ms)

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)

-- REAPER master: quadraphony on outputs 1-2 and 3-4
local master = reaper.GetMasterTrack(0)
if reaper.GetMediaTrackInfo_Value(master, "I_NCHAN") < 4 then
  reaper.SetMediaTrackInfo_Value(master, "I_NCHAN", 4)
end
add_hw_out(master, 0, 0)
add_hw_out(master, 2, 2)

-- E4L Master (quad decoder)
local e4l = find_track("E4L Master") or new_track("E4L Master")
reaper.SetMediaTrackInfo_Value(e4l, "I_NCHAN", NCH)
reaper.SetMediaTrackInfo_Value(e4l, "B_MAINSEND", 1)
local fx = find_fx(e4l, "E4L Master Bus")
if fx < 0 then fx = add_fx(e4l, "E4L Master Bus.jsfx", "E4L Master Bus (3rd order ambisonics decoder)") end
set_param(e4l, fx, "Decoder", 2)              -- Quad
set_param(e4l, fx, "Sub Output (channel, 0 = off)", 0)   -- the sub is fed from the master

-- CUE: binaural copy of the loops for the headphones
local cue = find_track("CUE (headphones)") or find_track("CUE (auriculares)")   -- older name
if not cue then
  cue = new_track("CUE (headphones)")
  reaper.SetMediaTrackInfo_Value(cue, "I_NCHAN", NCH)
  reaper.SetMediaTrackInfo_Value(cue, "B_MAINSEND", 0)
  local cfx = add_fx(cue, "E4L Master Bus.jsfx", "E4L Master Bus (3rd order ambisonics decoder)")
  set_param(cue, cfx, "Decoder", 0)           -- Binaural
  add_hw_out(cue, 0, cue_ch - 1)
end
add_send(e4l, cue, NCH, 1)                    -- pre-FX: the ambisonics mix

-- SYNTH IN: monitored input, to the headphones only
if not existing then E4L.add_input(in_ch, in_stereo, cue_ch) end

-- LOOP tracks, placed after the existing ones (before E4L Master)
for _ = 1, n_loops do E4L.add_loop(stereo_pan, lat_ms) end

reaper.PreventUIRefresh(-1)
reaper.TrackList_AdjustWindows(false)
reaper.Undo_EndBlock("E4L: live looper template", -1)

-- sub: everything that reaches the master also goes to the sub output
if sub_ch > 0 and not E4L_TEMPLATE_NO_SUB then
  local dir = DIR
  local GetUserInputs = reaper.GetUserInputs
  reaper.GetUserInputs = function() return true, tostring(sub_ch) end
  E4L_SUB_QUIET = true
  local okf, err = pcall(dofile, dir .. "E4L - Add sub to master.lua")
  E4L_SUB_QUIET = nil
  reaper.GetUserInputs = GetUserInputs
  if not okf then msg("Sub: " .. tostring(err)) end
end

if not E4L_TEMPLATE_QUIET then msg(string.format(
  "Done: %d LOOP tracks.\n\n" ..
  "Headphones: outputs %d-%d (SYNTH IN + binaural CUE).\n" ..
  "Route those outputs to the headphones in the interface's control panel.\n" ..
  "Quadraphony: outputs 1-4.%s\n" ..
  "Recording latency compensation: %.1f ms.\n\n" ..
  "Press play in REAPER and record from the E4L Live Panel.",
  n_loops, cue_ch, cue_ch + 1, sub_ch > 0 and ("  Sub: output " .. sub_ch .. ".") or "", lat_ms)) end
