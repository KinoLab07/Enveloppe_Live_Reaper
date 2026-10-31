-- E4L - Binaural mix of the session.lua
-- Envelop for REAPER: turns a session recorded with the Live Panel's "● REC" (the 4 speaker
-- feeds on "REC 1-2 (speakers)" and "REC 3-4 (speakers)") into a binaural stereo file for
-- headphones.
--
-- The 4 recorded speaker feeds are played as 4 virtual speakers at their real places
-- (1 = -45, 2 = +45, 3 = +135, 4 = -135: E4L Quad Panner, spread 90, LR) and decoded to
-- binaural with the same HRTF filters as the CUE (headphones) track (E4L Master Bus, Binaural).
-- The recorded items are copied: the REC tracks are not changed.
--
-- It builds:
--   BIN 1-2, BIN 3-4    copies of the recorded items (no master send)
--   BINAURAL MIX        Quad Panner + Master Bus (Binaural), no master send
-- and opens REAPER's Render window ready to render that track only (stem), stereo, over the
-- recording, to "Session binaural" in the project folder: press Render.
-- Running it again rebuilds those tracks (after a new recording).
-- GPLv2 or later (same as Envelop for Live).

local DIR = debug.getinfo(1, "S").source:match("@?(.*[/\\])") or ""
local E4L = dofile(DIR .. "e4l_lib.lua")
local function msg(s) E4L.msg(s, "E4L - Binaural mix") end

-- 1. the recording
local recs = {}
for _, d in ipairs(E4L.SESSION_TRACKS) do recs[#recs + 1] = E4L.find_track(d[1]) or false end
if not recs[1] or not recs[2] or
   reaper.CountTrackMediaItems(recs[1]) + reaper.CountTrackMediaItems(recs[2]) == 0 then
  msg("There is no recorded session yet.\n\nPress ● REC in the Live Panel, play, and stop: the " ..
      "recording goes on the tracks REC 1-2 and REC 3-4. Then run this script again.")
  return
end
local t0, t1 = math.huge, -math.huge
for _, tr in ipairs(recs) do
  for i = 0, reaper.CountTrackMediaItems(tr) - 1 do
    local it = reaper.GetTrackMediaItem(tr, i)
    local p = reaper.GetMediaItemInfo_Value(it, "D_POSITION")
    t0 = math.min(t0, p); t1 = math.max(t1, p + reaper.GetMediaItemInfo_Value(it, "D_LENGTH"))
  end
end

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)

-- 2. rebuild the mix tracks
for _, name in ipairs({ "BINAURAL MIX", "BIN 1-2", "BIN 3-4" }) do
  local tr = E4L.find_track(name)
  if tr then E4L.delete_track(tr) end
end

local mix = E4L.new_track("BINAURAL MIX")
reaper.SetMediaTrackInfo_Value(mix, "I_NCHAN", E4L.NCH)
reaper.SetMediaTrackInfo_Value(mix, "B_MAINSEND", 0)
local qfx = E4L.add_fx(mix, "E4L Quad Panner.jsfx", "E4L Quad Panner (3rd order ambisonics)")
E4L.set_param(mix, qfx, "Azimuth", 0)
E4L.set_param(mix, qfx, "Azimuth Spread", 90)          -- the 4 inputs on the 4 speaker places
E4L.set_param(mix, qfx, "Azimuth Spread Mode", 0)      -- LR: FL -45, FR 45, RL -135, RR 135
E4L.set_param(mix, qfx, "Radius", 0.1)                 -- at the speakers (distance 1)
local dfx = E4L.add_fx(mix, "E4L Master Bus.jsfx", "E4L Master Bus (3rd order ambisonics decoder)")
E4L.set_param(mix, dfx, "Decoder", 0)                  -- Binaural

-- copies of the recorded items on BIN 1-2 / BIN 3-4, sent (mono, channel by channel) to the
-- Quad Panner's inputs: FL, FR, RL, RR. Speaker 3 is +135 (rear right), speaker 4 -135 (rear left).
local routes = { { 0, 1 }, { 3, 2 } }   -- per REC track: its channel 1 -> input, channel 2 -> input
for k, rec in ipairs(recs) do
  local bin = E4L.new_track(k == 1 and "BIN 1-2" or "BIN 3-4")
  reaper.SetMediaTrackInfo_Value(bin, "I_NCHAN", 2)
  reaper.SetMediaTrackInfo_Value(bin, "B_MAINSEND", 0)
  for i = 0, reaper.CountTrackMediaItems(rec) - 1 do
    local it = reaper.GetTrackMediaItem(rec, i)
    local tk = reaper.GetActiveTake(it)
    local file = tk and reaper.GetMediaSourceFileName(reaper.GetMediaItemTake_Source(tk), "")
    local src = file and file ~= "" and reaper.PCM_Source_CreateFromFile(file)
    if src then
      local ni = reaper.AddMediaItemToTrack(bin)
      local nt = reaper.AddTakeToMediaItem(ni)
      reaper.SetMediaItemTake_Source(nt, src)
      reaper.SetMediaItemInfo_Value(ni, "D_POSITION", reaper.GetMediaItemInfo_Value(it, "D_POSITION"))
      reaper.SetMediaItemInfo_Value(ni, "D_LENGTH", reaper.GetMediaItemInfo_Value(it, "D_LENGTH"))
      reaper.SetMediaItemTakeInfo_Value(nt, "D_STARTOFFS", reaper.GetMediaItemTakeInfo_Value(tk, "D_STARTOFFS"))
      reaper.UpdateItemInProject(ni)
    end
  end
  for ch = 0, 1 do
    local s = reaper.CreateTrackSend(bin, mix)
    reaper.SetTrackSendInfo_Value(bin, 0, s, "I_SRCCHAN", 1024 + ch)
    reaper.SetTrackSendInfo_Value(bin, 0, s, "I_DSTCHAN", 1024 + routes[k][ch + 1])
    reaper.SetTrackSendInfo_Value(bin, 0, s, "I_SENDMODE", 0)
  end
end

-- 3. render settings: only BINAURAL MIX (stem), stereo, over the recording
for i = 0, reaper.CountTracks(0) - 1 do reaper.SetTrackSelected(reaper.GetTrack(0, i), false) end
reaper.SetTrackSelected(mix, true)
reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 2, true)       -- stems (selected tracks) only
reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)     -- custom time bounds
reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", t0, true)
reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", t1, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", reaper.GetProjectPath(""), true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "Session binaural", true)

reaper.PreventUIRefresh(-1)
reaper.TrackList_AdjustWindows(false)
reaper.Undo_EndBlock("E4L: binaural mix of the session", -1)

reaper.Main_OnCommand(40015, 0)   -- File: Render... (everything is filled in: press Render)
