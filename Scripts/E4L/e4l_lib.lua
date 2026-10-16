-- e4l_lib.lua  (not an action: shared code of the E4L live scripts)
-- Envelop for REAPER. GPLv2 or later (same as Envelop for Live).
--
--   local E4L = dofile(dir .. "e4l_lib.lua")
--
-- Track layout of a live project:
--   SYNTH IN, SYNTH IN 2, ...   inputs from the interface (monitored, to the headphones only)
--   LOOP 1, LOOP 2, ...         E4L Looper + E4L panner, fed by one of the inputs
--   AUDIO 1, AUDIO 2, ...       pre-recorded audio, looped on the timeline, + E4L panner
--   E4L Master                  E4L Master Bus = Quad -> REAPER master (+ E4L Sub Out)
--   CUE (auriculares)           binaural copy for the headphones

local E = {}
E.NCH = 16
E.SPREAD = { -45, 45, 135, -135, 0, 90, 180, -90 }

function E.msg(s, title) reaper.ShowMessageBox(s, title or "E4L", 0) end

---------------------------------------------------------------------------------------
-- tracks / FX / parameters
function E.track_name(tr)
  local _, n = reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)
  return n
end

function E.find_track(name)
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if E.track_name(tr) == name then return tr end
  end
end

-- tracks whose name matches a Lua pattern, in project order
function E.tracks_matching(pattern)
  local t = {}
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if E.track_name(tr):match(pattern) then t[#t + 1] = tr end
  end
  return t
end

function E.synth_inputs()
  local t = {}
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local n = E.track_name(tr)
    if n == "SYNTH IN" or n:match("^SYNTH IN %d+$") then t[#t + 1] = tr end
  end
  return t
end

function E.track_index(tr) return math.floor(reaper.GetMediaTrackInfo_Value(tr, "IP_TRACKNUMBER")) - 1 end

function E.new_track(name, idx)
  idx = idx or reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
  return tr
end

function E.add_fx(track, file, desc)
  for _, name in ipairs({ "JS:E4L/" .. file, "E4L/" .. file, "JS: " .. desc }) do
    local idx = reaper.TrackFX_AddByName(track, name, false, -1)
    if idx >= 0 then return idx end
  end
  E.msg("No se pudo cargar " .. file .. "\nCopia la carpeta Effects/E4L en la carpeta de recursos de REAPER.")
  return -1
end

function E.find_fx(track, pattern)
  for i = 0, reaper.TrackFX_GetCount(track) - 1 do
    local _, name = reaper.TrackFX_GetFXName(track, i, "")
    if name:find(pattern, 1, true) then return i end
  end
  return -1
end

-- set a JSFX slider by its exact name (value in the slider's own range)
function E.set_param(track, fx, pname, value)
  if fx < 0 then return end
  for p = 0, reaper.TrackFX_GetNumParams(track, fx) - 1 do
    local _, n = reaper.TrackFX_GetParamName(track, fx, p, "")
    if n == pname then reaper.TrackFX_SetParam(track, fx, p, value) return end
  end
end

function E.find_send(src, dst)
  for i = 0, reaper.GetTrackNumSends(src, 0) - 1 do
    if reaper.GetTrackSendInfo_Value(src, 0, i, "P_DESTTRACK") == dst then return i end
  end
  return -1
end

-- send of `nch` channels (2 or 16) from src to dst; mode 0 post-fader, 1 pre-FX, 3 pre-fader
function E.add_send(src, dst, nch, mode, muted)
  local s = E.find_send(src, dst)
  if s < 0 then
    s = reaper.CreateTrackSend(src, dst)
    reaper.SetTrackSendInfo_Value(src, 0, s, "I_SRCCHAN", nch == 2 and 0 or ((nch // 2) << 10))
    reaper.SetTrackSendInfo_Value(src, 0, s, "I_DSTCHAN", 0)
    reaper.SetTrackSendInfo_Value(src, 0, s, "I_SENDMODE", mode)
  end
  if muted ~= nil then reaper.SetTrackSendInfo_Value(src, 0, s, "B_MUTE", muted and 1 or 0) end
  return s
end

-- hardware output: track channels src_ch.. -> interface outputs dst_ch.. (0-based)
function E.add_hw_out(tr, src_ch, dst_ch, mono)
  for i = 0, reaper.GetTrackNumSends(tr, 1) - 1 do
    if math.floor(reaper.GetTrackSendInfo_Value(tr, 1, i, "I_DSTCHAN")) & 1023 == dst_ch then return end
  end
  local flag = mono and 1024 or 0
  local s = reaper.CreateTrackSend(tr, nil)
  reaper.SetTrackSendInfo_Value(tr, 1, s, "I_SRCCHAN", src_ch | flag)
  reaper.SetTrackSendInfo_Value(tr, 1, s, "I_DSTCHAN", dst_ch | flag)
end

---------------------------------------------------------------------------------------
-- project settings remembered in the project file
function E.cfg_get(key, default)
  local ok, v = reaper.GetProjExtState(0, "E4L", key)
  if ok and ok > 0 and v ~= "" then return tonumber(v) or v end
  return default
end

function E.cfg_set(key, value) reaper.SetProjExtState(0, "E4L", key, tostring(value)) end

-- recording latency compensation = audio input + output latency of the interface
function E.latency_ms()
  local inl, outl = reaper.GetInputOutputLatency()
  local okr, sr = reaper.GetAudioDeviceInfo("SRATE", "")
  sr = tonumber(sr) or 0
  if okr and sr > 0 then return (inl + outl) / sr * 1000 end
  return 0
end

---------------------------------------------------------------------------------------
-- building blocks
local function add_panner(tr, stereo, azimuth)
  local pfx = stereo and E.add_fx(tr, "E4L Stereo Panner.jsfx", "E4L Stereo Panner (3rd order ambisonics)")
                     or E.add_fx(tr, "E4L Mono Panner.jsfx", "E4L Mono Panner (3rd order ambisonics)")
  E.set_param(tr, pfx, "Azimuth", azimuth)
  E.set_param(tr, pfx, "Radius", 0.1)               -- full level (distance 1)
  return pfx
end

-- position (track index) right before E4L Master, or at the end
local function before_master()
  local m = E.find_track("E4L Master")
  return m and E.track_index(m) or reaper.CountTracks(0)
end

-- creates SYNTH IN / SYNTH IN 2 / ...: input ch (1-based), mono or stereo
function E.add_input(in_ch, stereo, cue_ch)
  local ins = E.synth_inputs()
  local name = #ins == 0 and "SYNTH IN" or ("SYNTH IN " .. (#ins + 1))
  local idx = #ins > 0 and (E.track_index(ins[#ins]) + 1) or 0
  local tr = E.new_track(name, idx)
  reaper.SetMediaTrackInfo_Value(tr, "I_RECINPUT", (stereo and 1024 or 0) + (in_ch - 1))
  reaper.SetMediaTrackInfo_Value(tr, "I_RECMODE", 2)    -- no recording, input monitoring only
  reaper.SetMediaTrackInfo_Value(tr, "I_RECARM", 1)
  reaper.SetMediaTrackInfo_Value(tr, "I_RECMON", 1)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  E.add_hw_out(tr, 0, (cue_ch or 7) - 1)
  -- feeds every existing loop, muted: each loop chooses its input
  for _, lp in ipairs(E.tracks_matching("^LOOP %d+$")) do E.add_send(tr, lp, 2, 3, #ins > 0) end
  return tr
end

-- creates the next LOOP n (looper + panner), fed by the first input
function E.add_loop(stereo_pan, lat_ms)
  local num = #E.tracks_matching("^LOOP %d+$") + 1
  local tr = E.new_track("LOOP " .. num, before_master())
  reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", E.NCH)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  local lfx = E.add_fx(tr, "E4L Looper.jsfx", "E4L Looper (bar-synced live looper)")
  E.set_param(tr, lfx, "Recording Latency Compensation (ms)", lat_ms or 0)
  add_panner(tr, stereo_pan, E.SPREAD[(num - 1) % #E.SPREAD + 1])
  for i, src in ipairs(E.synth_inputs()) do E.add_send(src, tr, 2, 3, i > 1) end
  local m = E.find_track("E4L Master")
  if m then E.add_send(tr, m, E.NCH, 0) end
  return tr
end

-- which input feeds a loop (index in synth_inputs(), 0 = none)
function E.loop_input(loop_tr)
  for i, src in ipairs(E.synth_inputs()) do
    local s = E.find_send(src, loop_tr)
    if s >= 0 and reaper.GetTrackSendInfo_Value(src, 0, s, "B_MUTE") < 0.5 then return i end
  end
  return 0
end

function E.set_loop_input(loop_tr, k)
  for i, src in ipairs(E.synth_inputs()) do E.add_send(src, loop_tr, 2, 3, i ~= k) end
end

-- bar length in seconds at a time position
function E.bar_seconds(t)
  local num, denom, bpm = reaper.TimeMap_GetTimeSigAtTime(0, t or 0)
  return (num or 4) * (4 / (denom or 4)) * 60 / (bpm or reaper.Master_GetTempo())
end

-- pre-recorded audio: AUDIO n track with a looped item from bar 1, muted until SONAR
function E.add_audio(file, stereo_pan)
  local num = #E.tracks_matching("^AUDIO %d+$") + 1
  local tr = E.new_track("AUDIO " .. num, before_master())
  reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", E.NCH)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
  add_panner(tr, stereo_pan ~= false, E.SPREAD[(num + 3) % #E.SPREAD + 1])
  local m = E.find_track("E4L Master")
  if m then E.add_send(tr, m, E.NCH, 0) end

  -- the file, at bar 1, looping
  reaper.SetOnlyTrackSelected(tr)
  local cur = reaper.GetCursorPosition()
  reaper.SetEditCurPos(0, false, false)
  reaper.InsertMedia(file, 0)
  reaper.SetEditCurPos(cur, false, false)
  local n = reaper.CountTrackMediaItems(tr)
  if n == 0 then return tr, 0 end
  local item = reaper.GetTrackMediaItem(tr, n - 1)
  local take = reaper.GetActiveTake(item)
  local len = reaper.GetMediaSourceLength(reaper.GetMediaItemTake_Source(take))
  local bar = E.bar_seconds(0)
  local bars = math.max(1, math.floor(len / bar + 0.5))
  local loop_len = len
  local ratio = len / (bars * bar)
  if math.abs(ratio - 1) < 0.1 then
    -- close to whole bars: adjust the speed, keeping the pitch
    reaper.SetMediaItemTakeInfo_Value(take, "D_PLAYRATE", ratio)
    reaper.SetMediaItemTakeInfo_Value(take, "B_PPITCH", 1)
    loop_len = bars * bar
  else
    bars = 0
  end
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "B_LOOPSRC", 1)
  local cover = 256 * bar                            -- repeat it for 256 bars
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", loop_len * math.max(1, math.ceil(cover / loop_len)))
  reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:E4L_bars", tostring(bars), true)
  return tr, bars
end

---------------------------------------------------------------------------------------
-- songs: saved set-ups (tracks, positions, animations, tempo; not the recorded loops)
function E.songs_dir()
  local d = reaper.GetResourcePath() .. "/E4L_Templates"
  reaper.RecursiveCreateDirectory(d, 0)
  return d
end

function E.list_songs()
  local d, t, i = E.songs_dir(), {}, 0
  while true do
    local f = reaper.EnumerateFiles(d, i)
    if not f then break end
    if f:lower():match("%.rpp$") then t[#t + 1] = f end
    i = i + 1
  end
  table.sort(t)
  return t, d
end

return E
