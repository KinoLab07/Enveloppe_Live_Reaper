-- e4l_lib.lua  (not an action: shared code of the E4L live scripts)
-- Envelop for REAPER. GPLv2 or later (same as Envelop for Live).
--
--   local E4L = dofile(dir .. "e4l_lib.lua")
--
-- Track layout of a live project:
--   SYNTH IN, SYNTH IN 2, ...   inputs from the interface (monitored, to the headphones only)
--   LOOP 1, LOOP 2, ...         E4L Looper + E4L panner, fed by all the inputs (or one of them)
--   AUDIO 1, AUDIO 2, ...       pre-recorded audio, looped on the timeline, + E4L panner
--   E4L Master                  E4L Master Bus = Quad -> REAPER master (+ E4L Sub Out)
--   CUE (headphones)            binaural copy for the headphones

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
  E.msg("Could not load " .. file .. "\nCopy the Effects/E4L folder into REAPER's resource folder.")
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
  -- feeds every existing loop that records from ALL the inputs (the default);
  -- loops set to one specific input get it muted
  for _, lp in ipairs(E.tracks_matching("^LOOP %d+$")) do E.add_send(tr, lp, 2, 3, E.loop_input(lp) ~= 0) end
  return tr
end

-- creates the next LOOP n (looper + panner), fed by all the inputs
function E.add_loop(stereo_pan, lat_ms)
  local num = #E.tracks_matching("^LOOP %d+$") + 1
  local tr = E.new_track("LOOP " .. num, before_master())
  reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", E.NCH)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  local lfx = E.add_fx(tr, "E4L Looper.jsfx", "E4L Looper (bar-synced live looper)")
  E.set_param(tr, lfx, "Recording Latency Compensation (ms)", lat_ms or 0)
  add_panner(tr, stereo_pan, E.SPREAD[(num - 1) % #E.SPREAD + 1])
  reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:E4L_in", "all", true)
  for _, src in ipairs(E.synth_inputs()) do E.add_send(src, tr, 2, 3, false) end
  local m = E.find_track("E4L Master")
  if m then E.add_send(tr, m, E.NCH, 0) end
  return tr
end

-- which input feeds a loop: 0 = ALL the inputs (default), k = only input k
function E.loop_input(loop_tr)
  local _, v = reaper.GetSetMediaTrackInfo_String(loop_tr, "P_EXT:E4L_in", "", false)
  return tonumber(v) or 0
end

-- loops made by older versions have no stored choice: they become ALL
function E.migrate_loop_input(loop_tr)
  local _, v = reaper.GetSetMediaTrackInfo_String(loop_tr, "P_EXT:E4L_in", "", false)
  if v == "" then E.set_loop_input(loop_tr, 0) end
end

function E.set_loop_input(loop_tr, k)
  reaper.GetSetMediaTrackInfo_String(loop_tr, "P_EXT:E4L_in", k == 0 and "all" or tostring(k), true)
  for i, src in ipairs(E.synth_inputs()) do E.add_send(src, loop_tr, 2, 3, k ~= 0 and i ~= k) end
end

-- bar length in seconds at a time position
function E.bar_seconds(t)
  local num, denom, bpm = reaper.TimeMap_GetTimeSigAtTime(0, t or 0)
  return (num or 4) * (4 / (denom or 4)) * 60 / (bpm or reaper.Master_GetTempo())
end

-- the E4L panner that fits a file with `nch` channels, placed on the speakers:
--   1 = Mono Panner, 2 = Stereo Panner (L/R on the front speakers 1-2),
--   3-4 = Quad Panner (each channel on its own speaker), 5+ = Multi-Panner (in a circle)
local function add_file_panner(tr, nch, mono_az)
  local pfx
  if nch <= 1 then
    pfx = E.add_fx(tr, "E4L Mono Panner.jsfx", "E4L Mono Panner (3rd order ambisonics)")
    E.set_param(tr, pfx, "Azimuth", mono_az)
  elseif nch == 2 then
    pfx = E.add_fx(tr, "E4L Stereo Panner.jsfx", "E4L Stereo Panner (3rd order ambisonics)")
    E.set_param(tr, pfx, "Azimuth", 0)
    E.set_param(tr, pfx, "Azimuth Spread", 45)      -- left -45 (speaker 1), right +45 (speaker 2)
  elseif nch <= 4 then
    pfx = E.add_fx(tr, "E4L Quad Panner.jsfx", "E4L Quad Panner (3rd order ambisonics)")
    E.set_param(tr, pfx, "Azimuth", 0)
    E.set_param(tr, pfx, "Azimuth Spread", 90)      -- FL -45, FR 45, RL -135, RR 135
    E.set_param(tr, pfx, "Azimuth Spread Mode", 0)
  else
    pfx = E.add_fx(tr, "E4L Multi-Panner.jsfx", "E4L Multi-Panner (3rd order ambisonics)")
    E.set_param(tr, pfx, "Azimuth", 0)
    for k = 1, 16 do
      E.set_param(tr, pfx, "Input " .. k .. " Active", k <= nch and 1 or 0)
      E.set_param(tr, pfx, "Input " .. k .. " Azimuth", k <= nch and ((k - 1) * 360 / nch + 180) % 360 - 180 or 0)
    end
  end
  E.set_param(tr, pfx, "Radius", 0.1)               -- full level (distance 1)
  return pfx
end

-- pre-recorded audio: AUDIO n track with a looped item from bar 1, muted until PLAY.
-- Returns the track (nil if the file cannot be read), its length in bars (0 = free) and
-- its number of channels.
function E.add_audio(file)
  -- the item is built directly (not with InsertMedia, which is REAPER's "Insert media
  -- file" action: it moves the cursor and can show import dialogs and stop the transport
  -- in the middle of a live set)
  local src = reaper.PCM_Source_CreateFromFile(file)
  if not src then return nil, 0, 0 end
  local len, is_qn = reaper.GetMediaSourceLength(src)
  if is_qn or not len or len <= 0 then reaper.PCM_Source_Destroy(src); return nil, 0, 0 end
  local nch = math.floor(reaper.GetMediaSourceNumChannels(src) or 1)

  local num = #E.tracks_matching("^AUDIO %d+$") + 1
  local tr = E.new_track("AUDIO " .. num, before_master())
  reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", E.NCH)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
  add_file_panner(tr, nch, E.SPREAD[(num + 3) % #E.SPREAD + 1])
  local m = E.find_track("E4L Master")
  if m then E.add_send(tr, m, E.NCH, 0) end

  -- the file, at bar 1, looping
  local item = reaper.AddMediaItemToTrack(tr)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", file:match("([^/\\]+)$") or file, true)
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
  reaper.UpdateItemInProject(item)
  reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:E4L_bars", tostring(bars), true)
  return tr, bars, nch
end

function E.delete_track(tr) reaper.DeleteTrack(tr) end

-- SYNC OUT: "E4L Sync Out" on its own track (no master send), its output 1 (reset pulse)
-- to the interface output `out_ch` (1-based, mono). Returns the track (existing or new).
function E.add_sync_out(out_ch)
  local tr = E.find_track("SYNC OUT")
  if not tr then
    tr = E.new_track("SYNC OUT")
    reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", 2)
    reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
    E.add_fx(tr, "E4L Sync Out.jsfx", "E4L Sync Out (reset / clock pulses for hardware sequencers)")
  end
  E.set_sync_output(tr, out_ch)
  return tr
end

-- interface output (1-based) of the SYNC OUT track: its only hardware output, mono
function E.set_sync_output(tr, out_ch)
  for i = reaper.GetTrackNumSends(tr, 1) - 1, 0, -1 do reaper.RemoveTrackSend(tr, 1, i) end
  E.add_hw_out(tr, 0, out_ch - 1, true)
  E.cfg_set("sync_ch", out_ch)
end

function E.sync_output(tr)
  if reaper.GetTrackNumSends(tr, 1) == 0 then return 0 end
  return (math.floor(reaper.GetTrackSendInfo_Value(tr, 1, 0, "I_DSTCHAN")) & 1023) + 1
end

-- which other track already sends to interface output `ch` (1-based): its name, or nil
function E.output_user(ch, except)
  local function uses(tr)
    for i = 0, reaper.GetTrackNumSends(tr, 1) - 1 do
      local d = math.floor(reaper.GetTrackSendInfo_Value(tr, 1, i, "I_DSTCHAN"))
      local mono = d & 1024 ~= 0
      local first = (d & 1023) + 1
      if ch == first or (not mono and ch == first + 1) then return true end
    end
  end
  local master = reaper.GetMasterTrack(0)
  if uses(master) then return "the speakers / sub (REAPER master)" end
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if tr ~= except and uses(tr) then return E.track_name(tr) end
  end
end

-- position inside the file of an AUDIO track (project seconds from the file's start).
-- The item starts at 0 and loops; where it is read from is set with the take's start offset.
local function audio_take(tr)
  local item = reaper.CountTrackMediaItems(tr) > 0 and reaper.GetTrackMediaItem(tr, 0)
  if not item then return end
  local take = reaper.GetActiveTake(item)
  if not take then return end
  local rate = reaper.GetMediaItemTakeInfo_Value(take, "D_PLAYRATE")
  local len = reaper.GetMediaSourceLength(reaper.GetMediaItemTake_Source(take))
  return item, take, (rate > 0 and rate or 1), len
end

function E.audio_pos(tr, t)
  local item, take, rate, len = audio_take(tr)
  if not item or len <= 0 then return 0 end
  local src = reaper.GetMediaItemTakeInfo_Value(take, "D_STARTOFFS")
            + (t - reaper.GetMediaItemInfo_Value(item, "D_POSITION")) * rate
  return (src % len) / rate
end

-- makes the file be at position `u` (project seconds from its start) at time `t`
function E.audio_set_pos(tr, t, u)
  local item, take, rate, len = audio_take(tr)
  if not item or len <= 0 then return end
  local offs = (u - (t - reaper.GetMediaItemInfo_Value(item, "D_POSITION"))) * rate
  reaper.SetMediaItemTakeInfo_Value(take, "D_STARTOFFS", offs % len)
  reaper.UpdateItemInProject(item)
end

-- paused position of an AUDIO track (nil = not paused)
function E.audio_paused(tr)
  local _, v = reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:E4L_pause", "", false)
  return tonumber(v)
end

function E.set_audio_paused(tr, u)
  reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:E4L_pause", u and tostring(u) or "", true)
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
