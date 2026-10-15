-- E4L - Live Looper template.lua
-- Envelop for REAPER: builds an Ableton-style live looping set-up for an analog synth,
-- spatialised in quadraphony with the E4L plugins.
--
--   SYNTH IN          audio input of the synth. Always to the headphones, never to the speakers.
--   LOOP 1..N         E4L Looper + E4L panner. Records N bars from the synth on the next bar
--                     and plays the loop in sync, spatialised, to "E4L Master".
--   E4L Master        E4L Master Bus = Quad (+ sub) -> REAPER master -> outputs 1-4 (+ sub output).
--   CUE (auriculares) binaural copy of the loops, to the headphone outputs.
--
-- Headphones: choose an output pair that is not a speaker, e.g. 7-8 on an Mbox Pro, and in the
-- interface's control panel set the headphone output source to that pair.
--
-- Running it again on a project that already has the template adds more LOOP tracks.
-- GPLv2 or later (same as Envelop for Live).

local NCH = 16

local function msg(s) reaper.ShowMessageBox(s, "E4L Live Looper", 0) end

local function find_track(name)
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local _, n = reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)
    if n == name then return tr end
  end
end

local function new_track(name, at_end_index)
  local idx = at_end_index or reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
  return tr
end

local function add_fx(track, file, desc)
  for _, name in ipairs({ "JS:E4L/" .. file, "E4L/" .. file, "JS: " .. desc }) do
    local idx = reaper.TrackFX_AddByName(track, name, false, -1)
    if idx >= 0 then return idx end
  end
  msg("Could not load " .. file .. "\nCopy the Effects/E4L folder into the REAPER resource folder.")
  return -1
end

local function find_fx(track, pattern)
  for i = 0, reaper.TrackFX_GetCount(track) - 1 do
    local _, name = reaper.TrackFX_GetFXName(track, i, "")
    if name:find(pattern, 1, true) then return i end
  end
  return -1
end

-- set a JSFX slider by its name (value in the slider's own range)
local function set_param(track, fx, pname, value)
  if fx < 0 then return end
  for p = 0, reaper.TrackFX_GetNumParams(track, fx) - 1 do
    local _, n = reaper.TrackFX_GetParamName(track, fx, p, "")
    if n == pname then reaper.TrackFX_SetParam(track, fx, p, value) return end
  end
end

local function has_send_to(src, dst)
  for i = 0, reaper.GetTrackNumSends(src, 0) - 1 do
    if reaper.GetTrackSendInfo_Value(src, 0, i, "P_DESTTRACK") == dst then return true end
  end
  return false
end

-- send of `nch` channels (2 or 16) from src to dst; mode 0 post-fader, 1 pre-FX, 3 pre-fader
local function add_send(src, dst, nch, mode)
  if has_send_to(src, dst) then return end
  local s = reaper.CreateTrackSend(src, dst)
  reaper.SetTrackSendInfo_Value(src, 0, s, "I_SRCCHAN", nch == 2 and 0 or ((nch // 2) << 10))
  reaper.SetTrackSendInfo_Value(src, 0, s, "I_DSTCHAN", 0)
  reaper.SetTrackSendInfo_Value(src, 0, s, "I_SENDMODE", mode)
end

-- hardware output: track channels src_ch.. -> interface outputs dst_ch.. (0-based)
-- stereo pair by default, single channel when mono is true
local function add_hw_out(tr, src_ch, dst_ch, mono)
  for i = 0, reaper.GetTrackNumSends(tr, 1) - 1 do
    if math.floor(reaper.GetTrackSendInfo_Value(tr, 1, i, "I_DSTCHAN")) & 1023 == dst_ch then return end
  end
  local flag = mono and 1024 or 0
  local s = reaper.CreateTrackSend(tr, nil)
  reaper.SetTrackSendInfo_Value(tr, 1, s, "I_SRCCHAN", src_ch | flag)
  reaper.SetTrackSendInfo_Value(tr, 1, s, "I_DSTCHAN", dst_ch | flag)
end

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

-- recording latency compensation = audio input + output latency of the interface
local lat_ms = 0
do
  local inl, outl = reaper.GetInputOutputLatency()
  local okr, sr = reaper.GetAudioDeviceInfo("SRATE", "")
  sr = tonumber(sr) or 0
  if okr and sr > 0 then lat_ms = (inl + outl) / sr * 1000 end
end

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)

-- REAPER master: quadraphony on outputs 1-2 and 3-4, plus the sub on its own output
local master = reaper.GetMasterTrack(0)
local mch = math.max(4, sub_ch)
mch = mch + (mch % 2)                          -- REAPER channel counts are even
if reaper.GetMediaTrackInfo_Value(master, "I_NCHAN") < mch then
  reaper.SetMediaTrackInfo_Value(master, "I_NCHAN", mch)
end
add_hw_out(master, 0, 0)
add_hw_out(master, 2, 2)
if sub_ch > 0 then add_hw_out(master, sub_ch - 1, sub_ch - 1, true) end

-- E4L Master (quad decoder)
local e4l = find_track("E4L Master") or new_track("E4L Master")
reaper.SetMediaTrackInfo_Value(e4l, "I_NCHAN", NCH)
reaper.SetMediaTrackInfo_Value(e4l, "B_MAINSEND", 1)
local fx = find_fx(e4l, "E4L Master Bus")
if fx < 0 then fx = add_fx(e4l, "E4L Master Bus.jsfx", "E4L Master Bus (3rd order ambisonics decoder)") end
set_param(e4l, fx, "Decoder", 2)              -- Quad
set_param(e4l, fx, "Sub Output (channel, 0 = off)", sub_ch)

-- CUE: binaural copy of the loops for the headphones
local cue = find_track("CUE (auriculares)")
if not cue then
  cue = new_track("CUE (auriculares)")
  reaper.SetMediaTrackInfo_Value(cue, "I_NCHAN", NCH)
  reaper.SetMediaTrackInfo_Value(cue, "B_MAINSEND", 0)
  local cfx = add_fx(cue, "E4L Master Bus.jsfx", "E4L Master Bus (3rd order ambisonics decoder)")
  set_param(cue, cfx, "Decoder", 0)           -- Binaural
  add_hw_out(cue, 0, cue_ch - 1)
end
add_send(e4l, cue, NCH, 1)                    -- pre-FX: the ambisonics mix

-- SYNTH IN: monitored input, to the headphones only
local synth = existing
if not synth then
  synth = new_track("SYNTH IN", 0)
  reaper.SetMediaTrackInfo_Value(synth, "I_RECINPUT", (in_stereo and 1024 or 0) + (in_ch - 1))
  reaper.SetMediaTrackInfo_Value(synth, "I_RECMODE", 2)    -- no recording, input monitoring only
  reaper.SetMediaTrackInfo_Value(synth, "I_RECARM", 1)
  reaper.SetMediaTrackInfo_Value(synth, "I_RECMON", 1)
  reaper.SetMediaTrackInfo_Value(synth, "B_MAINSEND", 0)
  add_hw_out(synth, 0, cue_ch - 1)
end

-- LOOP tracks, placed after the existing ones (before E4L Master)
local count = 0
for i = 0, reaper.CountTracks(0) - 1 do
  local _, n = reaper.GetSetMediaTrackInfo_String(reaper.GetTrack(0, i), "P_NAME", "", false)
  if n:match("^LOOP %d+$") then count = count + 1 end
end
local SPREAD = { -45, 45, 135, -135, 0, 90, 180, -90 }
local insert_at = reaper.GetMediaTrackInfo_Value(e4l, "IP_TRACKNUMBER") - 1
for k = 1, n_loops do
  local num = count + k
  local tr = new_track("LOOP " .. num, insert_at)
  insert_at = insert_at + 1
  reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", NCH)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  local lfx = add_fx(tr, "E4L Looper.jsfx", "E4L Looper (bar-synced live looper)")
  set_param(tr, lfx, "Recording Latency Compensation (ms)", lat_ms)
  local pfx = stereo_pan and add_fx(tr, "E4L Stereo Panner.jsfx", "E4L Stereo Panner (3rd order ambisonics)")
                          or add_fx(tr, "E4L Mono Panner.jsfx", "E4L Mono Panner (3rd order ambisonics)")
  set_param(tr, pfx, "Azimuth", SPREAD[(num - 1) % #SPREAD + 1])
  set_param(tr, pfx, "Radius", 0.1)            -- full level (distance 1)
  add_send(synth, tr, 2, 3)                    -- synth -> looper input (pre-fader)
  add_send(tr, e4l, NCH, 0)                    -- loop -> quad
end

reaper.PreventUIRefresh(-1)
reaper.TrackList_AdjustWindows(false)
reaper.Undo_EndBlock("E4L: live looper template", -1)

msg(string.format(
  "Listo: %d pistas LOOP.\n\n" ..
  "Auriculares: salidas %d-%d (SYNTH IN + CUE binaural).\n" ..
  "Asigna esas salidas a los auriculares en el panel de control de la interfaz.\n" ..
  "Cuadrafonia: salidas 1-4.%s\n" ..
  "Compensacion de latencia de grabacion: %.1f ms.\n\n" ..
  "Pulsa PLAY en REAPER y usa REC en el E4L Looper de cada pista.",
  n_loops, cue_ch, cue_ch + 1, sub_ch > 0 and ("  Sub: salida " .. sub_ch .. ".") or "", lat_ms))
