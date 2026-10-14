-- E4L - Setup session.lua
-- Envelop for REAPER: prepares the ambisonics routing that E4L does automatically in Live.
--
--  * Creates (or reuses) a track named "E4L Master" with 16 channels and "E4L Master Bus".
--  * Every selected track becomes a source: 16 channels, an E4L panner, no master send,
--    and a 16-channel send to "E4L Master".
--  * With no track selected, it creates a new source track.
--
-- GPLv2 or later (same as Envelop for Live).

local MASTER_NAME = "E4L Master"
local NCH = 16

local function add_fx(track, file, desc)
  local tries = { "JS:E4L/" .. file, "E4L/" .. file, "JS: " .. desc }
  for _, name in ipairs(tries) do
    local idx = reaper.TrackFX_AddByName(track, name, false, -1)
    if idx >= 0 then return idx end
  end
  reaper.ShowMessageBox("Could not load " .. file ..
    "\nCopy the Effects/E4L folder into the REAPER resource folder (Options > Show REAPER resource path).",
    "E4L", 0)
  return -1
end

local function has_fx(track, pattern)
  for i = 0, reaper.TrackFX_GetCount(track) - 1 do
    local _, name = reaper.TrackFX_GetFXName(track, i, "")
    if name:find(pattern, 1, true) then return true end
  end
  return false
end

local function find_master()
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local _, name = reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)
    if name == MASTER_NAME then return tr end
  end
  return nil
end

local function has_send_to(src, dst)
  for i = 0, reaper.GetTrackNumSends(src, 0) - 1 do
    if reaper.GetTrackSendInfo_Value(src, 0, i, "P_DESTTRACK") == dst then return true end
  end
  return false
end

local function setup_source(tr, master, panner_file, panner_desc)
  reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", NCH)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  if not has_fx(tr, "E4L") then add_fx(tr, panner_file, panner_desc) end
  if not has_send_to(tr, master) then
    local s = reaper.CreateTrackSend(tr, master)
    -- 16 channels: low 10 bits = first channel, (value >> 10) = channel count / 2
    reaper.SetTrackSendInfo_Value(tr, 0, s, "I_SRCCHAN", (NCH // 2) << 10)
    reaper.SetTrackSendInfo_Value(tr, 0, s, "I_DSTCHAN", 0)
  end
end

local PANNERS = {
  { "E4L Stereo Panner.jsfx", "E4L Stereo Panner (3rd order ambisonics)" },
  { "E4L Mono Panner.jsfx",   "E4L Mono Panner (3rd order ambisonics)" },
  { "E4L Source Panner.jsfx", "E4L Source Panner (3rd order ambisonics)" },
}

local ok, answer = reaper.GetUserInputs("E4L setup", 1,
  "Panner (1=Stereo 2=Mono 3=Source)", "1")
if not ok then return end
local choice = PANNERS[tonumber(answer) or 1] or PANNERS[1]

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)

local master = find_master()
if not master then
  reaper.InsertTrackAtIndex(reaper.CountTracks(0), true)
  master = reaper.GetTrack(0, reaper.CountTracks(0) - 1)
  reaper.GetSetMediaTrackInfo_String(master, "P_NAME", MASTER_NAME, true)
end
reaper.SetMediaTrackInfo_Value(master, "I_NCHAN", NCH)
reaper.SetMediaTrackInfo_Value(master, "B_MAINSEND", 1)
if not has_fx(master, "E4L Master Bus") then
  add_fx(master, "E4L Master Bus.jsfx", "E4L Master Bus (3rd order ambisonics decoder)")
end

local sel = {}
for i = 0, reaper.CountSelectedTracks(0) - 1 do
  local tr = reaper.GetSelectedTrack(0, i)
  if tr ~= master then sel[#sel + 1] = tr end
end
if #sel == 0 then
  local idx = reaper.GetMediaTrackInfo_Value(master, "IP_TRACKNUMBER") - 1
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "E4L Source", true)
  sel[1] = tr
end
for _, tr in ipairs(sel) do setup_source(tr, master, choice[1], choice[2]) end

reaper.PreventUIRefresh(-1)
reaper.TrackList_AdjustWindows(false)
reaper.Undo_EndBlock("E4L: setup session", -1)
