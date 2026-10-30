-- E4L - Live Panel.lua
-- Envelop for REAPER: one window to play the whole live looper set-up.
--
--   * big bar / beat counter, tempo and time signature, play / stop
--   * one row per track with an "E4L Looper": state, length, record / play / overdub / clear,
--     loop position with its bars, and a MOVEMENT button
--   * MOVEMENT opens the movement editor of that loop: which E4L effect, position,
--     automatic rotation (azimuth LFO), up and down (elevation LFO), stereo width and its
--     "breathing" (spread LFO), and quick presets. No need to open the plugins.
--   * room view (seen from above) with every loop: drag a dot to move that loop
--   * toolbar: + LOOP, + AUDIO (pre-recorded file, looped in sync), + INPUT (another input
--     of the interface), SAVE / LOAD TEMPLATE (set-ups saved as templates), NEW TEMPLATE
--
-- Keys: Space = play / stop, 1-9 = record on loop 1-9, 0 = stop all loops, Esc = close editor.
-- Right-click the header to dock / undock the panel inside REAPER.
-- GPLv2 or later (same as Envelop for Live).

local TITLE = "E4L Live Panel"
local EXT = "E4L_LivePanel"
local DIR = debug.getinfo(1, "S").source:match("@?(.*[/\\])") or ""
local E4L = dofile(DIR .. "e4l_lib.lua")
local TOP = 116          -- y where the rows / editor / room start (below the toolbar)

---------------------------------------------------------------------------------------
-- parameters
local function strip(n) return (n or ""):gsub("^%-", "") end

local function param_names(tr, fx)
  local t = {}
  for p = 0, reaper.TrackFX_GetNumParams(tr, fx) - 1 do
    local _, n = reaper.TrackFX_GetParamName(tr, fx, p, "")
    t[strip(n)] = p
  end
  return t
end

local function find_prefix(names, prefix)
  for n, p in pairs(names) do if n:sub(1, #prefix) == prefix then return p end end
  return -1
end

local function getp(tr, fx, p) if fx < 0 or not p or p < 0 then return 0 end return (reaper.TrackFX_GetParam(tr, fx, p)) end
local function setp(tr, fx, p, v) if fx >= 0 and p and p >= 0 then reaper.TrackFX_SetParam(tr, fx, p, v) end end

local LENGTHS = { 1, 2, 4, 8, 16, 32 }
local SYNC_LABELS = { "1/4", "1/2", "1", "2", "3", "4", "6", "8", "16", "32", "64" }
local STATE_NAME = { [0] = "EMPTY", "WAITING", "RECORDING", "PLAYING", "STOPPED", "PAUSED" }

-- E4L effects that can follow the looper
local EFFECTS = {
  { key = "Mono",   file = "E4L Mono Panner.jsfx",   desc = "E4L Mono Panner (3rd order ambisonics)",
    label = "One point (Mono Panner)" },
  { key = "Stereo", file = "E4L Stereo Panner.jsfx", desc = "E4L Stereo Panner (3rd order ambisonics)",
    label = "Two points, left and right (Stereo Panner)" },
  { key = "Source", file = "E4L Source Panner.jsfx", desc = "E4L Source Panner (3rd order ambisonics)",
    label = "Fixed position, no animation (Source Panner)" },
  { key = "Quad", file = "E4L Quad Panner.jsfx", desc = "E4L Quad Panner (3rd order ambisonics)",
    label = "Four points, for quad files (Quad Panner)" },
  { key = "Multi", match = "E4L Multi-Panner", file = "E4L Multi-Panner.jsfx",
    desc = "E4L Multi-Panner (3rd order ambisonics)", label = "Many points, for 5+ channel files (Multi-Panner)" },
}

local function effect_of(name)
  for i, e in ipairs(EFFECTS) do
    if name:find(e.match or ("E4L " .. e.key .. " Panner"), 1, true) then return i end
  end
  return 0
end

-- directions of the channels of a panner around its centre azimuth (for the room view)
local function channel_dirs(L, az)
  local key = EFFECTS[L.effect] and EFFECTS[L.effect].key
  local sp = (L.p.cur_sp and L.p.cur_sp >= 0) and getp(L.tr, L.pfx, L.p.cur_sp)
             or (L.p.sp and L.p.sp >= 0) and getp(L.tr, L.pfx, L.p.sp) or 0
  if key == "Stereo" then return { az - sp, az + sp }, { "L", "R" } end
  if key == "Quad" then
    return { az - sp / 2, az + sp / 2, az + 180 + sp / 2, az + 180 - sp / 2 }, {}
  end
end

---------------------------------------------------------------------------------------
-- scan the project for loopers (cached, refreshed twice a second)
local loops, last_scan = {}, -1
n_inputs = 1
inputs = {}

local function scan()
  local list = {}
  for t = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, t)
    local lfx, pfx, pname = -1, -1, ""
    for i = 0, reaper.TrackFX_GetCount(tr) - 1 do
      local _, name = reaper.TrackFX_GetFXName(tr, i, "")
      if lfx < 0 and name:find("E4L Looper", 1, true) then lfx = i
      elseif pfx < 0 and name:find("E4L", 1, true) and name:find("Panner", 1, true) then pfx, pname = i, name end
    end
    if lfx < 0 and pfx >= 0 then
      -- a spatialised track without looper: pre-recorded audio
      local _, tname = reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)
      local pn = param_names(tr, pfx)
      local _, bars = reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:E4L_bars", "", false)
      list[#list + 1] = {
        kind = "audio", tr = tr, name = tname ~= "" and tname or ("Track " .. (t + 1)), lfx = -1, pfx = pfx,
        effect = effect_of(pname), pn = pn, bars = tonumber(bars) or 0,
        p = { az = pn["Azimuth"] or -1, cur_az = pn["Current Azimuth"] or -1, sp = pn["Azimuth Spread"] or -1, cur_sp = pn["Current Spread"] or -1,
              cur_d = pn["Current Distance"] or -1 },
      }
    end
    if lfx >= 0 then
      local _, tname = reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)
      local ln = param_names(tr, lfx)
      local pn = pfx >= 0 and param_names(tr, pfx) or {}
      E4L.migrate_loop_input(tr)
      list[#list + 1] = {
        kind = "loop", input = E4L.loop_input(tr),
        tr = tr, name = tname ~= "" and tname or ("Track " .. (t + 1)), lfx = lfx, pfx = pfx,
        effect = pfx >= 0 and effect_of(pname) or 0, pn = pn,
        p = {
          len = find_prefix(ln, "Length"), rec = ln["Record"], play = ln["Play"],
          odub = ln["Overdub"], clear = ln["Clear"], pause = ln["Pause"], status = find_prefix(ln, "Status"),
          pend = find_prefix(ln, "Pending"), bars = ln["Loop Bars"], start = find_prefix(ln, "Loop Start"),
          qn = find_prefix(ln, "Loop Length"),
          az = pn["Azimuth"] or -1, cur_az = pn["Current Azimuth"] or -1, sp = pn["Azimuth Spread"] or -1, cur_sp = pn["Current Spread"] or -1,
          cur_d = pn["Current Distance"] or -1,
        },
      }
    end
  end
  loops = list
  inputs = E4L.synth_inputs()
  n_inputs = #inputs
end

---------------------------------------------------------------------------------------
-- drawing / widgets
local function rgb(r, g, b, a) gfx.set(r, g, b, a or 1) end
local function rect(x, y, w, h, fill) gfx.rect(x, y, w, h, fill == nil and 1 or fill) end

local function text(s, x, y, w, h, align)  -- align: nil left, 1 center, 2 right
  local tw, th = gfx.measurestr(s)
  if align == 1 and w then gfx.x = x + (w - tw) / 2
  elseif align == 2 and w then gfx.x = x + w - tw
  else gfx.x = x end
  gfx.y = h and (y + (h - th) / 2) or y
  gfx.drawstr(s)
end

local mouse_down, mouse_was_down, clicked = false, false, false
local drag, slider_drag = nil, nil

local function hit(x, y, w, h)
  return gfx.mouse_x >= x and gfx.mouse_x < x + w and gfx.mouse_y >= y and gfx.mouse_y < y + h
end

local function button(label, x, y, w, h, on, r, g, b)
  if on then rgb(r, g, b) else rgb(0.22, 0.22, 0.26) end
  rect(x, y, w, h)
  if on then rgb(0.05, 0.05, 0.05) else rgb(0.88, 0.88, 0.92) end
  text(label, x, y, w, h, 1)
  return clicked and hit(x, y, w, h)
end

-- segmented choice: returns the clicked index (1-based) or nil
local function segmented(opts, current, x, y, w, h)
  local n = #opts
  local bw = (w - (n - 1) * 3) / n
  local res
  for i, o in ipairs(opts) do
    if button(o, x + (i - 1) * (bw + 3), y, bw, h, i == current, 0.45, 0.75, 1) then res = i end
  end
  return res
end

-- horizontal slider; id must be unique. Returns the new value while dragging, or nil.
local function hslider(id, x, y, w, h, v, vmin, vmax, label, valtext)
  rgb(0.85, 0.85, 0.9); text(label, x, y - 17)
  rgb(0.7, 0.85, 1); text(valtext, x, y - 17, w, nil, 2)
  rgb(0.2, 0.2, 0.24); rect(x, y, w, h)
  local f = (v - vmin) / (vmax - vmin)
  f = math.max(0, math.min(1, f))
  rgb(0.35, 0.6, 0.95); rect(x, y, w * f, h)
  rgb(1, 1, 1); rect(x + w * f - 2, y - 2, 4, h + 4)
  if clicked and hit(x, y - 4, w, h + 8) then slider_drag = id end
  if slider_drag == id and mouse_down then
    local nf = math.max(0, math.min(1, (gfx.mouse_x - x) / w))
    return vmin + nf * (vmax - vmin)
  end
end

local function section(title, x, y, w)
  rgb(0.45, 0.75, 1); text(title, x, y)
  rgb(0.3, 0.3, 0.36); gfx.line(x, y + 18, x + w, y + 18)
end

---------------------------------------------------------------------------------------
-- human-readable values
local function az_text(a)
  a = ((a + 180) % 360) - 180
  local r = math.floor(a + 0.5)
  if math.abs(r) <= 2 then return "0°  front" end
  if math.abs(r) >= 178 then return "180°  back" end
  return string.format("%d°  %s", math.abs(r), r > 0 and "right" or "left")
end

local function el_text(e)
  local r = math.floor(e + 0.5)
  if r == 0 then return "0°  ear level" end
  return string.format("%d°  %s", math.abs(r), r > 0 and "up" or "down")
end

local function dist_text(radius, range)
  local d = radius * range
  local db = d < 1 and 0 or -1.5 * (d - 1)
  if d < 0.999 then return string.format("%.2f  (very close, full level)", d) end
  if d < 1.05 then return string.format("%.1f  (full level)", d) end
  return string.format("%.1f  (%.1f dB)", d, db)
end

local function speed_text(hz) if hz <= 0 then return "-" end return string.format("1 turn every %.1f s", 1 / hz) end

---------------------------------------------------------------------------------------
-- changing the E4L effect of a loop: replace the panner, keep the shared settings
local function set_effect(L, idx)
  local e = EFFECTS[idx]
  if not e or idx == L.effect then return end
  reaper.Undo_BeginBlock()
  local keep = {}
  if L.pfx >= 0 then
    for n, p in pairs(L.pn) do keep[n] = getp(L.tr, L.pfx, p) end
    reaper.TrackFX_Delete(L.tr, L.pfx)
  end
  local fx = -1
  for _, name in ipairs({ "JS:E4L/" .. e.file, "E4L/" .. e.file, "JS: " .. e.desc }) do
    fx = reaper.TrackFX_AddByName(L.tr, name, false, -1)
    if fx >= 0 then break end
  end
  if fx >= 0 then
    local names = param_names(L.tr, fx)
    for n, v in pairs(keep) do
      if names[n] and not n:find("^Current") then setp(L.tr, fx, names[n], v) end
    end
    if keep["Azimuth Spread"] and names["Azimuth-Spread"] then setp(L.tr, fx, names["Azimuth-Spread"], keep["Azimuth Spread"]) end
    if names["Coordinate Mode"] then setp(L.tr, fx, names["Coordinate Mode"], 1) end   -- polar
  end
  reaper.Undo_EndBlock("E4L: spatial effect of " .. L.name, -1)
  last_scan = -1
end

-- quick movement presets (Mono / Stereo panners)
local PRESETS = {
  { "Still", { ["Azimuth LFO On/Off"] = 0, ["Elevation LFO On/Off"] = 0, ["Azimuth Spread LFO On/Off"] = 0,
              ["Random Wander On/Off"] = 0 } },
  { "Slow turn", { ["Azimuth LFO On/Off"] = 1, ["Azimuth LFO Mode"] = 0, ["Azimuth LFO Time Mode"] = 0,
                    ["Azimuth LFO Frequency (Hz)"] = 0.1, ["Azimuth LFO Rate"] = 1, ["Random Wander On/Off"] = 0 } },
  { "4-bar turn", { ["Azimuth LFO On/Off"] = 1, ["Azimuth LFO Mode"] = 0, ["Azimuth LFO Time Mode"] = 1,
                         ["Azimuth LFO Sync (bars)"] = 5, ["Azimuth LFO Direction"] = 0, ["Random Wander On/Off"] = 0 } },
  { "Whirl", { ["Azimuth LFO On/Off"] = 1, ["Azimuth LFO Mode"] = 0, ["Azimuth LFO Time Mode"] = 0,
                  ["Azimuth LFO Frequency (Hz)"] = 1, ["Azimuth LFO Rate"] = 1, ["Random Wander On/Off"] = 0 } },
  { "Front swing", { ["Azimuth"] = 0, ["Azimuth LFO On/Off"] = 1, ["Azimuth LFO Mode"] = 1,
                         ["Azimuth LFO Time Mode"] = 0, ["Azimuth LFO Frequency (Hz)"] = 0.25,
                         ["Azimuth LFO Rate"] = 1, ["Azimuth LFO Depth"] = 45, ["Random Wander On/Off"] = 0 } },
  { "Right swing", { ["Azimuth"] = 90, ["Azimuth LFO On/Off"] = 1, ["Azimuth LFO Mode"] = 1,
                        ["Azimuth LFO Time Mode"] = 0, ["Azimuth LFO Frequency (Hz)"] = 0.25,
                        ["Azimuth LFO Rate"] = 1, ["Azimuth LFO Depth"] = 45, ["Random Wander On/Off"] = 0 } },
  { "Back swing", { ["Azimuth"] = 180, ["Azimuth LFO On/Off"] = 1, ["Azimuth LFO Mode"] = 1,
                        ["Azimuth LFO Time Mode"] = 0, ["Azimuth LFO Frequency (Hz)"] = 0.25,
                        ["Azimuth LFO Rate"] = 1, ["Azimuth LFO Depth"] = 45, ["Random Wander On/Off"] = 0 } },
  { "Left swing", { ["Azimuth"] = -90, ["Azimuth LFO On/Off"] = 1, ["Azimuth LFO Mode"] = 1,
                        ["Azimuth LFO Time Mode"] = 0, ["Azimuth LFO Frequency (Hz)"] = 0.25,
                        ["Azimuth LFO Rate"] = 1, ["Azimuth LFO Depth"] = 45, ["Random Wander On/Off"] = 0 } },
  { "Wander", { ["Random Wander On/Off"] = 1, ["Random Wander Time Mode"] = 0,
                ["Random Wander Rate (Hz)"] = 0.25, ["Random Wander Area"] = 1, ["Azimuth LFO On/Off"] = 0 } },
  { "Wander 1 bar", { ["Random Wander On/Off"] = 1, ["Random Wander Time Mode"] = 1,
                      ["Random Wander Sync (bars)"] = 2, ["Random Wander Area"] = 1, ["Azimuth LFO On/Off"] = 0 } },
}

---------------------------------------------------------------------------------------
-- transport info
local function transport()
  local ps = reaper.GetPlayState()
  local playing = ps & 1 == 1
  local t = playing and reaper.GetPlayPosition() or reaper.GetCursorPosition()
  local beat_in_bar, measure, beats_per_bar = reaper.TimeMap2_timeToBeats(0, t)
  local num, denom, bpm = reaper.TimeMap_GetTimeSigAtTime(0, t)
  local qn = reaper.TimeMap2_timeToQN(0, t)
  return {
    playing = playing, bar = math.floor(measure) + 1,
    beat = math.floor(beat_in_bar) + 1,
    bpb = math.floor((beats_per_bar or num or 4) + 0.5), num = num or 4, denom = denom or 4,
    bpm = bpm or reaper.Master_GetTempo(), qn = qn, time = t,
  }
end

---------------------------------------------------------------------------------------
local editing = nil   -- index of the loop whose movement editor is open
local confirm_del = nil   -- { tr = track, t = time } after a first click on DELETE

-- audio tracks: PLAY / MUTE switch on the next bar, like the loops
local pend_mute, last_bar = {}, nil
local function apply_pending(tp)
  if (not tp.playing) or (last_bar and tp.bar ~= last_bar) then
    for tr, m in pairs(pend_mute) do
      if reaper.ValidatePtr2 == nil or reaper.ValidatePtr2(0, tr, "MediaTrack*") then
        reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", m)
        if m == 0 then E4L.set_audio_paused(tr, nil) end
      end
    end
    pend_mute = {}
  end
  last_bar = tp.bar
end

-- time of the next bar line (or where playback will start, when stopped)
local function next_bar_time(tp)
  if not tp.playing then return reaper.GetCursorPosition() end
  local bq = tp.num * 4 / tp.denom
  return reaper.TimeMap2_QNToTime(0, (math.floor(tp.qn / bq + 0.000001) + 1) * bq)
end

-- AUDIO track PLAY: from the beginning of the file on the next bar / stop on the next bar.
-- The read position is only moved while the track is silent, so no jump is heard.
local function audio_play(L, tp)
  local muted = reaper.GetMediaTrackInfo_Value(L.tr, "B_MUTE") > 0.5
  local pm = pend_mute[L.tr]
  if not muted then
    if pm == 1 then pend_mute[L.tr] = nil else pend_mute[L.tr] = 1 end
  elseif pm == 0 then
    pend_mute[L.tr] = nil
  else
    E4L.audio_set_pos(L.tr, next_bar_time(tp), 0)
    pend_mute[L.tr] = 0
  end
end

-- AUDIO track PAUSE: silent at once, remembering where it was; PAUSE again: continues on the
-- next bar from the bar of the file where it was paused (from that exact point if the file
-- is not a whole number of bars)
local function audio_pause(L, tp)
  local muted = reaper.GetMediaTrackInfo_Value(L.tr, "B_MUTE") > 0.5
  local paused = E4L.audio_paused(L.tr)
  if not muted then
    E4L.set_audio_paused(L.tr, E4L.audio_pos(L.tr, tp.time))
    reaper.SetMediaTrackInfo_Value(L.tr, "B_MUTE", 1)
    pend_mute[L.tr] = nil
  elseif paused then
    if pend_mute[L.tr] == 0 then pend_mute[L.tr] = nil return end
    local u = paused
    if L.bars > 0 then
      local bs = E4L.bar_seconds(tp.time)
      u = math.floor(u / bs + 0.000001) * bs
    end
    E4L.audio_set_pos(L.tr, next_bar_time(tp), u)
    pend_mute[L.tr] = 0
  end
end

local status_text, status_time = "", 0
local function status(t) status_text, status_time = t, reaper.time_precise() end

---------------------------------------------------------------------------------------
-- toolbar actions
local function act_add_loop()
  reaper.Undo_BeginBlock()
  local tr = E4L.add_loop(E4L.cfg_get("stereo_pan", 0) == 1, E4L.cfg_get("lat_ms", E4L.latency_ms()))
  reaper.Undo_EndBlock("E4L: + loop", -1)
  last_scan = -1
  status(E4L.track_name(tr) .. " added.")
end

local function is_stopped() return reaper.GetPlayState() % 2 == 0 end

-- adds an AUDIO track for `file`. `why` = what already stopped the transport (diagnostics)
local function add_audio_file(file, why)
  local was_playing = not is_stopped()
  reaper.Undo_BeginBlock()
  local tr, bars, nch = E4L.add_audio(file)
  reaper.Undo_EndBlock("E4L: + audio", -1)
  last_scan = -1
  if was_playing and is_stopped() then why = "while adding the track" end
  local note = why and ("  [REAPER's play stopped " .. why .. " - restarted]") or ""
  local fname = file:match("([^/\\]+)$") or file
  if not tr then status("REAPER could not read " .. fname .. note) return end
  local kind = nch == 1 and "mono" or nch == 2 and "stereo" or nch == 4 and "quad" or (nch .. " channels")
  status(E4L.track_name(tr) .. " (" .. kind .. ")" ..
         (bars > 0 and (": " .. bars .. " bars, fitted to the tempo") or ": plays at its own speed") ..
         ". MUTED: press its PLAY." .. note)
end

local function act_add_audio()
  local was_playing = not is_stopped()
  local ok, file = reaper.GetUserFileNameForRead("", "Choose a pre-recorded audio file", "wav;aif;aiff;mp3;flac;ogg")
  local why = (was_playing and is_stopped()) and "while the file window was open" or nil
  if not ok or file == "" then
    if why then status("REAPER's play stopped " .. why .. " - restarted. Tip: drag files onto the panel.") end
    return
  end
  add_audio_file(file, why)
end

local AUDIO_EXT = { wav = true, aif = true, aiff = true, mp3 = true, flac = true, ogg = true, m4a = true }

local function act_add_input()
  local ins = E4L.synth_inputs()
  local ok, csv = reaper.GetUserInputs("New input", 2,
    "Interface input (channel),1 mono 2 stereo", tostring(#ins + 1) .. ",1")
  if not ok then return end
  local ch, st = csv:match("^%s*(%d+)%s*,%s*(%d+)")
  if not ch then return end
  reaper.Undo_BeginBlock()
  local tr = E4L.add_input(tonumber(ch), tonumber(st) == 2, E4L.cfg_get("cue_ch", 7))
  reaper.Undo_EndBlock("E4L: + input", -1)
  last_scan = -1
  status(E4L.track_name(tr) .. " (input " .. ch .. ") added. Loops set to ALL record it; IN n = one input only.")
end

local function act_save_song()
  local _, dir = E4L.list_songs()
  local cur = reaper.GetProjectName(0, ""):gsub("%.[Rr][Pp][Pp]$", "")
  local ok, name = reaper.GetUserInputs("Save template", 1, "Template name,extrawidth=150",
                                        cur ~= "" and cur or "Template 1")
  if not ok or name == "" then return end
  name = name:gsub("[/\\:%*%?\"<>|]", "-")
  reaper.Main_SaveProjectEx(0, dir .. "/" .. name .. ".RPP", 0)
  status("Template \"" .. name .. "\" saved (tracks, positions, movements and tempo).")
end

local function act_load_song()
  local songs, dir = E4L.list_songs()
  if #songs == 0 then status("No saved templates yet.") return end
  local items = {}
  for i, f in ipairs(songs) do items[i] = f:gsub("%.[Rr][Pp][Pp]$", "") end
  gfx.x, gfx.y = gfx.mouse_x, gfx.mouse_y
  local m = gfx.showmenu(table.concat(items, "|"))
  if m > 0 then
    reaper.Main_openProject(dir .. "/" .. songs[m])
    editing = nil; last_scan = -1
    status("Template \"" .. items[m] .. "\" loaded. Loops start empty.")
  end
end

local function act_new_song()
  local f = DIR .. "E4L - New live project.lua"
  local ok, err = pcall(dofile, f)
  if not ok then status("Error: " .. tostring(err)) end
  editing = nil; last_scan = -1
end

-- SYNC: reset pulse for an external sequencer ("E4L Sync Out" on the SYNC OUT track).
-- Adds the track (asking for the interface output) or opens its window if it exists.
local function ask_sync_output(default)
  local ok, v = reaper.GetUserInputs("Sync out", 1, "Pulses to interface output (channel)", tostring(default))
  local ch = ok and tonumber(v)
  if not ch or ch < 1 then return end
  return math.floor(ch)
end

local function sync_warning(ch, tr)
  local who = E4L.output_user(ch, tr)
  return who and ("  WARNING: output " .. ch .. " is also used by " .. who ..
                  " - the pulses would mix with that sound. Use a free output.") or ""
end

local function sync_label()
  local tr = E4L.find_track("SYNC OUT")
  if not tr then return "+ SYNC" end
  return E4L.sync_enabled(tr) and "SYNC" or "SYNC OFF"
end

local function act_sync()
  local tr = E4L.find_track("SYNC OUT")
  if tr then
    gfx.x, gfx.y = gfx.mouse_x, gfx.mouse_y
    local now = E4L.sync_output(tr)
    local on = E4L.sync_enabled(tr)
    local m = gfx.showmenu((on and "Turn sync OFF (no pulses)" or "Turn sync ON") ..
                           "|Settings (reset / clock, pulse, test)|Send the pulses to output... (now " .. now .. ")" ..
                           "|Remove the SYNC OUT track")
    if m == 1 then
      E4L.set_sync_enabled(tr, not on)
      status(on and "Sync OFF: no pulses. SYNC > Turn sync ON to send them again." or "Sync ON.")
    elseif m == 4 then
      reaper.Undo_BeginBlock()
      E4L.delete_track(tr)
      reaper.Undo_EndBlock("E4L: remove sync out", -1)
      status("SYNC OUT removed (+ SYNC adds it again).")
    end
    m = m - 1
    if m == 1 then
      local fx = E4L.find_fx(tr, "E4L Sync Out")
      if fx >= 0 then reaper.TrackFX_Show(tr, fx, 3) end
    elseif m == 2 then
      local ch = ask_sync_output(now)
      if not ch then return end
      reaper.Undo_BeginBlock()
      E4L.set_sync_output(tr, ch)
      reaper.Undo_EndBlock("E4L: sync output", -1)
      status("SYNC OUT now sends its pulses to output " .. ch .. "." .. sync_warning(ch, tr))
    end
    return
  end
  local ch = ask_sync_output(E4L.cfg_get("sync_ch", 6))
  if not ch then return end
  reaper.Undo_BeginBlock()
  tr = E4L.add_sync_out(ch)
  reaper.Undo_EndBlock("E4L: sync out", -1)
  status("SYNC OUT added on output " .. ch .. " (settings: SYNC)." .. sync_warning(ch, tr))
end

-- runs a toolbar action without ever killing the panel; with keep_playing the transport is
-- restarted if something stopped it (the loops only sound while REAPER is playing)
local restart_check = nil   -- time at which we verify that REAPER really plays again
local function run_action(fn, keep_playing)
  local was_playing = reaper.GetPlayState() % 2 == 1
  local t0, pos = reaper.time_precise(), reaper.GetPlayPosition()
  local ok, err = pcall(fn)
  if not ok then status("Error: " .. tostring(err)) end
  if keep_playing and was_playing and reaper.GetPlayState() % 2 == 0 then
    local cur = reaper.GetCursorPosition()
    reaper.SetEditCurPos(pos + reaper.time_precise() - t0, false, false)
    reaper.OnPlayButton()
    reaper.SetEditCurPos(cur, false, false)
    restart_check = reaper.time_precise() + 1
  end
end

local function check_restart()
  if restart_check and reaper.time_precise() > restart_check then
    restart_check = nil
    if reaper.GetPlayState() % 2 == 0 then
      status("REAPER does not play again: the audio interface may have stopped. " ..
             "Options > Preferences > Audio > Device > Apply, then PLAY.")
    end
  end
end

-- audio files dragged from the Finder onto the panel: no file window during the set
local function check_dropped_files()
  if not gfx.getdropfile then return end
  local files, i = {}, 0
  while true do
    local r, f = gfx.getdropfile(i)
    if not r or r == 0 then break end
    files[#files + 1] = f; i = i + 1
  end
  if #files == 0 then return end
  gfx.getdropfile(-1)
  for _, f in ipairs(files) do
    local ext = (f:match("%.([%w]+)$") or ""):lower()
    if AUDIO_EXT[ext] then run_action(function() add_audio_file(f) end, true)
    else status("Not an audio file: " .. (f:match("([^/\\]+)$") or f)) end
  end
end

local function draw_toolbar(W)
  local y, h = 80, 28
  local items = {
    { "+ LOOP", 80, act_add_loop, true }, { "+ AUDIO", 84, act_add_audio, true },
    { "+ INPUT", 84, act_add_input, true },
    { "SAVE TEMPLATE", 140, act_save_song }, { "LOAD TEMPLATE", 140, act_load_song },
    { "NEW TEMPLATE", 130, act_new_song },
    { sync_label(), 76, act_sync },
  }
  local x = 8
  for _, it in ipairs(items) do
    if button(it[1], x, y, it[2], h, false) then run_action(it[3], it[4]) end
    x = x + it[2] + 6
  end
  if status_text ~= "" and reaper.time_precise() - status_time < 8 then
    rgb(0.7, 0.85, 1); text(status_text, x + 8, y, nil, h)
  end
end

-- STOP goes back to bar 1: on PLAY loops and audio files start from their beginning (like
-- Ableton). PAUSE keeps the position: PLAY continues where it was.
local function play_stop()
  if reaper.GetPlayState() % 2 == 1 then
    reaper.OnStopButton()
    reaper.SetEditCurPos(0, true, false)
    for _, L in ipairs(loops) do
      if L.kind == "audio" then E4L.audio_set_pos(L.tr, 0, 0) end
    end
  else
    reaper.OnPlayButton()
  end
end

-- REC: records the whole session (what goes to the speakers) on the REC 1-2 / REC 3-4 tracks
local function rec_session()
  if reaper.GetPlayState() & 4 == 4 then play_stop() return end   -- recording: stop
  reaper.Undo_BeginBlock()
  local trs, err = E4L.session_rec_tracks()
  reaper.Undo_EndBlock("E4L: session recording tracks", -1)
  if not trs then status(err) return end
  reaper.Main_OnCommand(1013, 0)                                     -- Transport: Record
  status("Recording the session (the 4 speakers) on REC 1-2 and REC 3-4. REC or STOP ends it.")
end

local function draw_header(tp, W)
  rgb(0.11, 0.11, 0.14); rect(0, 0, W, 74)
  gfx.setfont(2)
  rgb(tp.playing and 0.35 or 0.7, tp.playing and 0.95 or 0.7, tp.playing and 0.5 or 0.75)
  text(string.format("%d . %d", tp.bar, tp.beat), 14, 6)
  gfx.setfont(1)
  rgb(0.6, 0.6, 0.65); text("bar . beat", 16, 54)

  local bx, bw, gap = 200, 26, 5
  for i = 1, tp.bpb do
    local x = bx + (i - 1) * (bw + gap)
    if tp.playing and i == tp.beat then
      if i == 1 then rgb(1, 0.55, 0.2) else rgb(0.35, 0.95, 0.5) end
    else rgb(0.25, 0.25, 0.3) end
    rect(x, 14, bw, 24)
  end
  local phrase = (tp.bar - 1) % 4 + 1
  for i = 1, 4 do
    if i == phrase then rgb(0.5, 0.75, 1) else rgb(0.25, 0.25, 0.3) end
    rect(bx + (i - 1) * 30, 44, 26, 8)
  end
  rgb(0.6, 0.6, 0.65); text("4-bar phrase", bx + 128, 41)

  -- input level meters: is the synth reaching REAPER?
  local mx = bx + 250
  for k, tr in ipairs(inputs) do
    local x = mx + (k - 1) * 104
    if x + 96 > W - 442 then break end
    local pk = math.max(reaper.Track_GetPeakInfo(tr, 0), reaper.Track_GetPeakInfo(tr, 1))
    local db = pk > 0 and 20 * math.log(pk, 10) or -90
    local f = math.max(0, math.min(1, (db + 60) / 60))
    rgb(0.6, 0.6, 0.65); text("IN " .. k, x, 14)
    rgb(0.2, 0.2, 0.24); rect(x + 34, 17, 60, 10)
    if db > -3 then rgb(1, 0.3, 0.3) elseif db > -12 then rgb(1, 0.8, 0.3) else rgb(0.35, 0.95, 0.5) end
    rect(x + 34, 17, 60 * f, 10)
  end
  if n_inputs > 0 then rgb(0.5, 0.5, 0.55); text("inputs", mx, 30) end

  local rx = math.max(bx + tp.bpb * (bw + gap) + 20, W - 350)
  local recording = reaper.GetPlayState() & 4 == 4
  local blink = math.floor(reaper.time_precise() * 2) % 2 == 0
  if button(recording and "■ REC" or "● REC", rx - 82, 36, 76, 28, recording and blink, 1, 0.3, 0.3) then rec_session() end
  rgb(0.85, 0.85, 0.9)
  text(string.format("%.1f BPM   %d/%d", tp.bpm, tp.num, tp.denom), rx, 12)
  if button(tp.playing and "STOP" or "PLAY", rx, 36, 96, 28, tp.playing, 0.35, 0.95, 0.5) then play_stop() end
  local paused = reaper.GetPlayState() & 2 == 2
  if button(paused and "PAUSED" or "PAUSE", rx + 102, 36, 80, 28, paused, 1, 0.8, 0.3) then reaper.OnPauseButton() end
  if button("STOP ALL LOOPS", rx + 188, 36, 150, 28, false) then
    for _, L in ipairs(loops) do
      if L.kind == "loop" then setp(L.tr, L.lfx, L.p.play, 0) else pend_mute[L.tr] = 1 end
    end
  end
end

local function draw_rows(tp, x0, y0, W, H)
  local rowh = math.max(26, math.min(40, math.floor((H - y0 - 6) / math.max(1, #loops))))
  gfx.setfont(1)
  if #loops == 0 then
    rgb(0.7, 0.7, 0.75)
    text("No loops yet. Press NEW TEMPLATE or + LOOP.", x0, y0 + 10)
    return
  end
  local col = { [0] = { 0.4, 0.4, 0.45 }, { 1, 0.6, 0.2 }, { 1, 0.3, 0.3 }, { 0.35, 0.95, 0.5 }, { 0.55, 0.7, 0.9 },
                { 1, 0.8, 0.3 } }
  -- button columns: REC, PLAY, PAUSE, OVERDUB (DELETE on audio rows), CLEAR, MOVEMENT
  local bx = x0 + 344
  local XR, XP, XPA, XO, XC, XM = bx, bx + 56, bx + 112, bx + 176, bx + 254, bx + 308
  for i, L in ipairs(loops) do
    local y = y0 + (i - 1) * rowh
    local bh = rowh - 16
    local sel = reaper.IsTrackSelected(L.tr)
    rgb(sel and 0.17 or 0.13, sel and 0.17 or 0.13, sel and 0.21 or 0.16); rect(x0, y, W, rowh - 4)
    rgb(0.88, 0.88, 0.92)
    text(string.format("%d  %s", i, L.name), x0 + 8, y, nil, rowh - 4)
    if clicked and hit(x0, y, 110, rowh - 4) then reaper.SetOnlyTrackSelected(L.tr) end
    local blink_on = math.floor(reaper.time_precise() * 4) % 2 == 0
    local px = x0 + 748                                   -- position bar
    local pw = W - (px - x0) - 6

    if L.kind == "loop" then
      local st = math.floor(getp(L.tr, L.lfx, L.p.status) + 0.5)
      local pend = math.floor(getp(L.tr, L.lfx, L.p.pend) + 0.5)
      local c = col[st] or col[0]
      local blink = (st == 1 or pend > 0) and blink_on
      rgb(c[1], c[2], c[3], blink and 0.45 or 1); rect(x0 + 110, y + 6, 96, bh)
      rgb(0.05, 0.05, 0.05)
      local label = STATE_NAME[st] or "?"
      if pend == 1 then label = "→ PLAY" elseif pend == 2 then label = "→ STOP" elseif pend == 3 then label = "→ RESUME" end
      text(label, x0 + 110, y + 6, 96, bh, 1)

      local li = math.floor(getp(L.tr, L.lfx, L.p.len) + 0.5)
      local nl = LENGTHS[li + 1] or 4
      if button(nl .. (nl == 1 and " bar" or " bars"), x0 + 212, y + 6, 74, bh, false) then
        setp(L.tr, L.lfx, L.p.len, (li + 1) % #LENGTHS)
      end
      -- input of the interface that feeds this loop (click to change)
      -- ALL = records every input of the interface; IN n = only that input (click to change)
      if button(L.input == 0 and "ALL" or ("IN " .. L.input), x0 + 290, y + 6, 50, bh, false) then
        local k = (L.input + 1) % (n_inputs + 1)
        E4L.set_loop_input(L.tr, k); L.input = k
      end

      if button("REC", XR, y + 6, 52, bh, st == 1 or st == 2, 1, 0.3, 0.3) then
        setp(L.tr, L.lfx, L.p.rec, getp(L.tr, L.lfx, L.p.rec) > 0.5 and 0 or 1)
      end
      local play_on = getp(L.tr, L.lfx, L.p.play) > 0.5
      if button("PLAY", XP, y + 6, 52, bh, play_on, 0.35, 0.95, 0.5) then
        setp(L.tr, L.lfx, L.p.play, play_on and 0 or 1)
      end
      local pause_on = getp(L.tr, L.lfx, L.p.pause) > 0.5
      if button(pause_on and "PAUSED" or "PAUSE", XPA, y + 6, 60, bh, pause_on, 1, 0.8, 0.3) then
        setp(L.tr, L.lfx, L.p.pause, pause_on and 0 or 1)
      end
      local od = getp(L.tr, L.lfx, L.p.odub) > 0.5
      if button("OVERDUB", XO, y + 6, 74, bh, od, 1, 0.75, 0.2) then
        setp(L.tr, L.lfx, L.p.odub, od and 0 or 1)
      end
      if button("CLEAR", XC, y + 6, 50, bh, false) then setp(L.tr, L.lfx, L.p.clear, 1) end
      if button("MOVEMENT", XM, y + 6, 90, bh, editing == i, 0.45, 0.75, 1) then
        editing = (editing == i) and nil or i
      end
      if pw > 30 then
        rgb(0.2, 0.2, 0.24); rect(px, y + 10, pw, rowh - 24)
        local lqn = getp(L.tr, L.lfx, L.p.qn)
        if (st == 2 or st == 3) and lqn > 0 and tp.playing then
          local ph = ((tp.qn - getp(L.tr, L.lfx, L.p.start)) / lqn) % 1
          if st == 2 then rgb(1, 0.3, 0.3, 0.9) else rgb(0.35, 0.95, 0.5, 0.9) end
          rect(px, y + 10, pw * ph, rowh - 24)
        end
        rgb(0.5, 0.5, 0.55)
        local nb = math.floor(getp(L.tr, L.lfx, L.p.bars) + 0.5)
        for k = 1, nb - 1 do gfx.line(px + pw * k / nb, y + 10, px + pw * k / nb, y + rowh - 15) end
      end
    else
      -- pre-recorded audio: PLAY (from its beginning) / STOP on the next bar, PAUSE now
      local muted = reaper.GetMediaTrackInfo_Value(L.tr, "B_MUTE") > 0.5
      local pm = pend_mute[L.tr]
      local paused = muted and E4L.audio_paused(L.tr) ~= nil
      local c = paused and col[5] or muted and col[0] or col[3]
      rgb(c[1], c[2], c[3], (pm ~= nil and blink_on) and 0.45 or 1); rect(x0 + 110, y + 6, 96, bh)
      rgb(0.05, 0.05, 0.05)
      local label = paused and "PAUSED" or muted and "STOPPED" or "PLAYING"
      if pm == 0 then label = paused and "→ RESUME" or "→ PLAY" elseif pm == 1 then label = "→ STOP" end
      text(label, x0 + 110, y + 6, 96, bh, 1)
      rgb(0.7, 0.7, 0.75)
      text(L.bars > 0 and ("audio · " .. L.bars .. " bars") or "audio", x0 + 212, y + 6, 128, bh)
      local want_on = (pm ~= nil) and (pm == 0 and not paused) or (pm == nil and not muted)
      if button("PLAY", XP, y + 6, 52, bh, want_on, 0.35, 0.95, 0.5) then audio_play(L, tp) end
      if button(paused and "PAUSED" or "PAUSE", XPA, y + 6, 60, bh, paused, 1, 0.8, 0.3) then audio_pause(L, tp) end
      if button("MOVEMENT", XM, y + 6, 90, bh, editing == i, 0.45, 0.75, 1) then
        editing = (editing == i) and nil or i
      end
      -- DELETE: a second click within 3 s confirms (no window in the middle of a set)
      local sure = confirm_del and confirm_del.tr == L.tr and reaper.time_precise() - confirm_del.t < 3
      if button(sure and "SURE?" or "DELETE", XO, y + 6, 74, bh, sure, 1, 0.3, 0.3) then
        if sure then
          confirm_del = nil
          reaper.Undo_BeginBlock()
          E4L.delete_track(L.tr)
          reaper.Undo_EndBlock("E4L: delete " .. L.name, -1)
          pend_mute[L.tr] = nil; editing = nil; last_scan = -1
          status(L.name .. " deleted (Cmd+Z in REAPER brings it back).")
          return
        end
        confirm_del = { tr = L.tr, t = reaper.time_precise() }
      end
      if pw > 30 then
        rgb(0.2, 0.2, 0.24); rect(px, y + 10, pw, rowh - 24)
        if L.bars > 0 and tp.playing and not muted then
          local ll = L.bars * E4L.bar_seconds(0)
          rgb(0.35, 0.95, 0.5, 0.9); rect(px, y + 10, pw * ((E4L.audio_pos(L.tr, tp.time) % ll) / ll), rowh - 24)
        end
        rgb(0.5, 0.5, 0.55)
        for k = 1, L.bars - 1 do gfx.line(px + pw * k / L.bars, y + 10, px + pw * k / L.bars, y + rowh - 15) end
      end
    end
  end
end

---------------------------------------------------------------------------------------
-- movement editor
local function draw_editor(x0, y0, W, H)
  local L = loops[editing]
  if not L then editing = nil return end
  local tr, fx, pn = L.tr, L.pfx, L.pn
  local function g(n) return getp(tr, fx, pn[n]) end
  local function s(n, v) setp(tr, fx, pn[n], v) end
  local function has(n) return pn[n] ~= nil end

  rgb(0.12, 0.12, 0.15); rect(x0, y0, W, H)
  gfx.setfont(3)
  rgb(0.9, 0.9, 0.95); text("Movement · " .. L.name, x0 + 10, y0 + 8)
  gfx.setfont(1)
  if button("← BACK TO THE LOOPS", x0 + W - 190, y0 + 8, 180, 26, false) then editing = nil return end

  -- effect selector
  rgb(0.85, 0.85, 0.9); text("E4L effect:", x0 + 10, y0 + 46)
  local cur = EFFECTS[L.effect]
  if button((cur and cur.label or "(none)") .. "  ▾", x0 + 100, y0 + 42, 340, 24, false) then
    gfx.x, gfx.y = x0 + 100, y0 + 66
    local items = {}
    for i, e in ipairs(EFFECTS) do items[#items + 1] = (i == L.effect and "!" or "") .. e.label end
    local m = gfx.showmenu(table.concat(items, "|"))
    if m > 0 then set_effect(L, m) end
  end
  if fx < 0 then
    rgb(1, 0.7, 0.3); text("This track has no E4L panner: choose an effect above.", x0 + 10, y0 + 90)
    return
  end

  local colw = math.floor((W - 40) / 2)
  local c1, c2 = x0 + 10, x0 + 30 + colw
  local y = y0 + 84

  -- ---------------- POSITION ----------------
  section("POSITION", c1, y, colw)
  rgb(0.55, 0.55, 0.6); text("(height is not heard in quad)", c1, y, colw, nil, 2)
  y = y + 42
  local v = hslider("az", c1, y, colw, 12, g("Azimuth"), -180, 180, "Direction", az_text(g("Azimuth")))
  if v then s("Azimuth", math.floor(v + 0.5)) end
  y = y + 40
  v = hslider("el", c1, y, colw, 12, g("Elevation"), -90, 90, "Height", el_text(g("Elevation")))
  if v then s("Elevation", math.floor(v + 0.5)) end
  y = y + 40
  local range = has("Range") and g("Range") or 10
  v = hslider("rad", c1, y, colw, 12, g("Radius"), 0, 1, "Distance", dist_text(g("Radius"), range))
  if v then s("Radius", math.floor(v * 1000 + 0.5) / 1000) end
  y = y + 30

  if not has("Azimuth LFO On/Off") then
    rgb(0.7, 0.7, 0.75); text("This effect has no animations. Choose One point or Two points.", c1, y + 10)
    return
  end

  -- ---------------- AUTOMATIC ROTATION (azimuth LFO) ----------------
  section("AUTOMATIC ROTATION", c1, y, colw); y = y + 26
  local on = g("Azimuth LFO On/Off") > 0.5
  if button(on and "ON" or "OFF", c1, y, 110, 24, on, 0.35, 0.95, 0.5) then s("Azimuth LFO On/Off", on and 0 or 1) end
  local k = segmented({ "Full turn", "Swing" }, math.floor(g("Azimuth LFO Mode") + 0.5) + 1, c1 + 118, y, colw - 118, 24)
  if k then s("Azimuth LFO Mode", k - 1) end
  y = y + 30
  local sync = g("Azimuth LFO Time Mode") > 0.5
  k = segmented({ "Free speed", "Tempo sync" }, sync and 2 or 1, c1, y, colw, 24)
  if k then s("Azimuth LFO Time Mode", k - 1) end
  y = y + 46
  if sync then
    local si = math.floor(g("Azimuth LFO Sync (bars)") + 0.5)
    v = hslider("async", c1, y, colw, 12, si, 0, 10, "One turn every", SYNC_LABELS[si + 1] .. " bar(s)")
    if v then s("Azimuth LFO Sync (bars)", math.floor(v + 0.5)) end
    y = y + 22
    k = segmented({ "Clockwise", "Counter-clockwise" }, math.floor(g("Azimuth LFO Direction") + 0.5) + 1, c1, y, colw, 24)
    if k then s("Azimuth LFO Direction", k - 1) end
  else
    local hz = g("Azimuth LFO Frequency (Hz)") * math.abs(g("Azimuth LFO Rate"))
    -- speed slider on a log scale, 0.02 .. 4 Hz
    local lv = math.log(math.max(hz, 0.02) / 0.02) / math.log(200)
    v = hslider("aspd", c1, y, colw, 12, lv, 0, 1, "Speed", speed_text(hz))
    if v then
      local nhz = 0.02 * 200 ^ v
      local sign = g("Azimuth LFO Rate") < 0 and -1 or 1
      local f = math.max(0.1, nhz)
      s("Azimuth LFO Frequency (Hz)", f); s("Azimuth LFO Rate", sign * nhz / f)
    end
    y = y + 22
    local ccw = g("Azimuth LFO Rate") < 0
    k = segmented({ "Clockwise", "Counter-clockwise" }, ccw and 2 or 1, c1, y, colw, 24)
    if k then s("Azimuth LFO Rate", (k == 2 and -1 or 1) * math.abs(g("Azimuth LFO Rate"))) end
  end
  y = y + 46
  if g("Azimuth LFO Mode") > 0.5 then
    v = hslider("adep", c1, y, colw, 12, g("Azimuth LFO Depth"), 0, 180, "Swing depth", string.format("± %d°", math.floor(g("Azimuth LFO Depth") + 0.5)))
    if v then s("Azimuth LFO Depth", math.floor(v + 0.5)) end
  end

  -- ---------------- COLUMN 2: UP AND DOWN, WIDTH, PRESETS ----------------
  y = y0 + 84
  section("UP AND DOWN (height)", c2, y, colw); y = y + 26
  on = g("Elevation LFO On/Off") > 0.5
  if button(on and "ON" or "OFF", c2, y, 110, 24, on, 0.35, 0.95, 0.5) then s("Elevation LFO On/Off", on and 0 or 1) end
  k = segmented({ "Up only", "Up and down" }, math.floor(g("Elevation LFO Polarity") + 0.5) + 1, c2 + 118, y, colw - 118, 24)
  if k then s("Elevation LFO Polarity", k - 1) end
  y = y + 46
  local ehz = g("Elevation LFO Frequency (Hz)")
  v = hslider("espd", c2, y, colw, 12, ehz, 0.1, 4, "Speed", speed_text(ehz))
  if v then s("Elevation LFO Frequency (Hz)", math.floor(v * 100 + 0.5) / 100) end
  y = y + 40
  v = hslider("edep", c2, y, colw, 12, g("Elevation LFO Depth"), 0, 90, "Depth", string.format("%d°", math.floor(g("Elevation LFO Depth") + 0.5)))
  if v then s("Elevation LFO Depth", math.floor(v + 0.5)) end
  y = y + 26

  if has("Random Wander On/Off") then
    section("RANDOM MOVEMENT (inside the room)", c2, y, colw); y = y + 26
    on = g("Random Wander On/Off") > 0.5
    if button(on and "ON" or "OFF", c2, y, 110, 24, on, 0.35, 0.95, 0.5) then s("Random Wander On/Off", on and 0 or 1) end
    local wsync = g("Random Wander Time Mode") > 0.5
    k = segmented({ "Free speed", "Tempo sync" }, wsync and 2 or 1, c2 + 118, y, colw - 118, 24)
    if k then s("Random Wander Time Mode", k - 1) end
    y = y + 46
    local hw = math.floor((colw - 16) / 2)          -- speed and area side by side
    if wsync then
      local si = math.floor(g("Random Wander Sync (bars)") + 0.5)
      v = hslider("wsync", c2, y, hw, 12, si, 0, 10, "New point", "every " .. SYNC_LABELS[si + 1] .. " bar(s)")
      if v then s("Random Wander Sync (bars)", math.floor(v + 0.5)) end
    else
      local whz = g("Random Wander Rate (Hz)")
      local lv = math.log(math.max(whz, 0.02) / 0.02) / math.log(200)
      v = hslider("wspd", c2, y, hw, 12, lv, 0, 1, "New point", string.format("every %.1f s", 1 / math.max(whz, 0.02)))
      if v then s("Random Wander Rate (Hz)", math.floor(0.02 * 200 ^ v * 1000 + 0.5) / 1000) end
    end
    local wa = g("Random Wander Area")
    v = hslider("warea", c2 + hw + 16, y, hw, 12, wa, 0, 1, "Area",
                wa >= 0.95 and "whole room" or wa < 0.35 and "near the centre" or string.format("%d%%", math.floor(wa * 100 + 0.5)))
    if v then s("Random Wander Area", math.floor(v * 100 + 0.5) / 100) end
    y = y + 26
  end

  if has("Azimuth Spread LFO On/Off") then
    section(EFFECTS[L.effect] and EFFECTS[L.effect].key == "Quad" and "WIDTH (quad)" or "STEREO WIDTH", c2, y, colw); y = y + 42
    v = hslider("sp", c2, y, colw, 12, g("Azimuth Spread"), 0, 180, "Left / right spread", string.format("± %d°", math.floor(g("Azimuth Spread") + 0.5)))
    if v then s("Azimuth Spread", math.floor(v + 0.5)) end
    y = y + 22
    on = g("Azimuth Spread LFO On/Off") > 0.5
    if button(on and "BREATHING" or "NO BREATHING", c2, y, 110, 24, on, 0.35, 0.95, 0.5) then s("Azimuth Spread LFO On/Off", on and 0 or 1) end
    local shz = g("Azimuth Spread LFO Frequency (Hz)")
    v = hslider("sspd", c2 + 118, y + 6, colw - 118, 12, shz, 0.01, 4, "", speed_text(shz))
    if v then s("Azimuth Spread LFO Frequency (Hz)", math.floor(v * 100 + 0.5) / 100) end
    y = y + 34
  end

  section("QUICK MOVEMENTS", c2, y, colw); y = y + 26
  local bw = (colw - 9) / 4
  for i, pr in ipairs(PRESETS) do
    local bx = c2 + ((i - 1) % 4) * (bw + 3)
    local by = y + math.floor((i - 1) / 4) * 28
    if button(pr[1], bx, by, bw, 24, false) then
      reaper.Undo_BeginBlock()
      for n, val in pairs(pr[2]) do s(n, val) end
      reaper.Undo_EndBlock("E4L: " .. pr[1], -1)
    end
  end
end

---------------------------------------------------------------------------------------
local function draw_room(x, y, size)
  local cx, cy, R = x + size / 2, y + size / 2, size / 2 - 22
  rgb(0.11, 0.11, 0.14); rect(x, y, size, size)
  rgb(0.3, 0.3, 0.36); gfx.circle(cx, cy, R, 0, 1)
  gfx.line(cx - R, cy, cx + R, cy); gfx.line(cx, cy - R, cx, cy + R)
  for k, a in ipairs({ -45, 45, 135, -135 }) do
    local r = math.rad(a)
    local sx, sy = cx + math.sin(r) * (R + 8), cy - math.cos(r) * (R + 8)
    rgb(0.55, 0.55, 0.6); rect(sx - 7, sy - 7, 14, 14)
    rgb(0.1, 0.1, 0.1); text(tostring(k), sx - 7, sy - 7, 14, 14, 1)
  end
  rgb(0.6, 0.6, 0.65); gfx.circle(cx, cy, 6, 0, 1); gfx.line(cx, cy - 6, cx, cy - 11)
  rgb(0.5, 0.5, 0.55); text("front", cx - 16, y + 2)

  for i, L in ipairs(loops) do
    if L.pfx >= 0 and L.p.az >= 0 then
      local az = L.p.cur_az >= 0 and getp(L.tr, L.pfx, L.p.cur_az) or getp(L.tr, L.pfx, L.p.az)
      if drag == i then az = getp(L.tr, L.pfx, L.p.az) end
      local r = math.rad(az)
      local dist = (L.p.cur_d and L.p.cur_d >= 0 and drag ~= i) and getp(L.tr, L.pfx, L.p.cur_d) or 1
      dist = dist > 0.001 and math.min(dist, 1.2) or 1      -- not published (yet): on the circle
      local dx, dy = cx + math.sin(r) * R * 0.78 * dist, cy - math.cos(r) * R * 0.78 * dist
      local st = L.kind == "loop" and math.floor(getp(L.tr, L.lfx, L.p.status) + 0.5)
                 or (reaper.GetMediaTrackInfo_Value(L.tr, "B_MUTE") > 0.5 and 0 or 3)
      local r0, g0, b0 = 0.5, 0.5, 0.6
      if st == 3 then r0, g0, b0 = 0.35, 0.95, 0.5 elseif st == 2 then r0, g0, b0 = 1, 0.3, 0.3 end
      local dirs, labels = channel_dirs(L, az)
      if dirs then
        for k, a in ipairs(dirs) do
          local ra = math.rad(a)
          local sx, sy = cx + math.sin(ra) * R * 0.95, cy - math.cos(ra) * R * 0.95
          rgb(r0, g0, b0, 0.2); gfx.line(dx, dy, sx, sy)
          if labels[k] then
            rgb(r0, g0, b0); gfx.circle(sx, sy, 7, 1, 1)
            rgb(0.05, 0.05, 0.05); text(labels[k], sx - 7, sy - 7, 14, 14, 1)
          else
            rgb(r0, g0, b0); gfx.circle(sx, sy, 5, 0, 1); gfx.circle(sx, sy, 4, 0, 1)
          end
        end
      end
      rgb(r0, g0, b0); gfx.circle(dx, dy, 11, 1, 1)
      if editing == i then rgb(0.45, 0.75, 1); gfx.circle(dx, dy, 15, 0, 1) end
      rgb(0.05, 0.05, 0.05); text(tostring(i), dx - 11, dy - 11, 22, 22, 1)
      if clicked and (gfx.mouse_x - dx) ^ 2 + (gfx.mouse_y - dy) ^ 2 < 14 ^ 2 then drag = i end
    end
  end
  if drag and mouse_down then
    local L = loops[drag]
    if L and L.pfx >= 0 then
      local az = math.deg(math.atan(gfx.mouse_x - cx, -(gfx.mouse_y - cy)))
      setp(L.tr, L.pfx, L.p.az, math.floor(az + 0.5))
    end
  elseif not mouse_down then drag = nil end
  rgb(0.5, 0.5, 0.55)
  text("drag a dot to move that loop", x + 6, y + size - 16)
end

---------------------------------------------------------------------------------------
local function keyboard(c)
  if c == 32 then play_stop() end                                        -- space
  if c >= 49 and c <= 57 then                                            -- 1-9: record
    local L = loops[c - 48]
    if L and L.kind == "loop" then setp(L.tr, L.lfx, L.p.rec, getp(L.tr, L.lfx, L.p.rec) > 0.5 and 0 or 1)
    elseif L then audio_play(L, transport()) end
  end
  if c == 48 then for _, L in ipairs(loops) do if L.kind == "loop" then setp(L.tr, L.lfx, L.p.play, 0) end end end  -- 0
end

local function main()
  local c = gfx.getchar()
  if c < 0 then
    reaper.SetExtState(EXT, "dock", tostring(gfx.dock(-1)), true)
    return
  end
  -- "E4L - Update from GitHub" asks the running panel to close, then opens the new version
  if reaper.GetExtState(EXT, "quit") == "1" then
    reaper.SetExtState(EXT, "quit", "", false)
    reaper.SetExtState(EXT, "dock", tostring(gfx.dock(-1)), true)
    reaper.SetExtState(EXT, "alive", "", false)
    gfx.quit()
    return
  end
  if c == 27 then
    if editing then editing = nil else gfx.quit() return end
  end

  local now = reaper.time_precise()
  if now - last_scan > 0.5 then scan(); last_scan = now end

  mouse_down = gfx.mouse_cap & 1 == 1
  clicked = mouse_down and not mouse_was_down
  if not mouse_down then slider_drag = nil end
  if c > 0 and c ~= 27 then keyboard(c) end

  local W, H = gfx.w, gfx.h
  rgb(0.08, 0.08, 0.1); rect(0, 0, W, H)
  local tp = transport()
  draw_header(tp, W)

  if gfx.mouse_cap & 2 == 2 and not RCLICK and gfx.mouse_y < 74 then
    RCLICK = true
    gfx.x, gfx.y = gfx.mouse_x, gfx.mouse_y
    local docked = gfx.dock(-1) & 1 == 1
    local m = gfx.showmenu(docked and "Undock" or "Dock inside REAPER")
    if m == 1 then gfx.dock(docked and 0 or 1) end
  elseif gfx.mouse_cap & 2 == 0 then RCLICK = false end

  draw_toolbar(W)
  check_dropped_files()
  check_restart()
  apply_pending(tp)
  local room = math.max(0, math.min(H - TOP - 6, math.floor(W * 0.32)))
  if W < 900 then room = 0 end
  local lw = W - room - 24
  if editing and not loops[editing] then editing = nil end
  if editing then draw_editor(8, TOP, lw, H - TOP - 8) else draw_rows(tp, 8, TOP, lw, H) end
  if room > 120 then draw_room(W - room - 8, TOP, room) end
  reaper.SetExtState(EXT, "alive", tostring(reaper.time_precise()), false)

  mouse_was_down = mouse_down
  gfx.update()
  reaper.defer(main)
end

local dock = tonumber(reaper.GetExtState(EXT, "dock")) or 0
gfx.init(TITLE, 1240, 680, dock)
gfx.setfont(1, "Arial", 15)
gfx.setfont(2, "Arial", 44, string.byte("b"))
gfx.setfont(3, "Arial", 20, string.byte("b"))
gfx.setfont(1)
scan()
main()
