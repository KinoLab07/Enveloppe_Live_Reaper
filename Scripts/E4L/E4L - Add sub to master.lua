-- E4L - Add sub to master.lua
-- Sends the sum of everything that reaches REAPER's master to a subwoofer output.
--   * adds "E4L Sub Out" to the master FX chain
--   * gives the master enough channels and a mono hardware output to the sub
--   * switches off the sub of every "E4L Master Bus" (so the sub is not fed twice)
-- Works on any project, e.g. one made with an earlier version of the templates.
-- GPLv2 or later (same as Envelop for Live).

local ok, v = reaper.GetUserInputs("E4L sub", 1, "Sub output (interface channel)", "5")
if not ok then return end
local sub_ch = math.floor(tonumber(v) or 5)
if sub_ch < 1 then return end

local function find_fx(track, pattern)
  for i = 0, reaper.TrackFX_GetCount(track) - 1 do
    local _, name = reaper.TrackFX_GetFXName(track, i, "")
    if name:find(pattern, 1, true) then return i end
  end
  return -1
end

local function set_param(track, fx, pname, value)
  if fx < 0 then return end
  for p = 0, reaper.TrackFX_GetNumParams(track, fx) - 1 do
    local _, n = reaper.TrackFX_GetParamName(track, fx, p, "")
    if n == pname then reaper.TrackFX_SetParam(track, fx, p, value) return end
  end
end

reaper.Undo_BeginBlock()
local master = reaper.GetMasterTrack(0)

-- channels: even number, at least the sub channel and the 4 quad channels
local mch = math.max(4, sub_ch); mch = mch + (mch % 2)
if reaper.GetMediaTrackInfo_Value(master, "I_NCHAN") < mch then
  reaper.SetMediaTrackInfo_Value(master, "I_NCHAN", mch)
end

-- mono hardware output: master channel sub_ch -> interface output sub_ch
local have = false
for i = 0, reaper.GetTrackNumSends(master, 1) - 1 do
  if math.floor(reaper.GetTrackSendInfo_Value(master, 1, i, "I_DSTCHAN")) & 1023 == sub_ch - 1 then have = true end
end
if not have then
  local s = reaper.CreateTrackSend(master, nil)
  reaper.SetTrackSendInfo_Value(master, 1, s, "I_SRCCHAN", (sub_ch - 1) | 1024)
  reaper.SetTrackSendInfo_Value(master, 1, s, "I_DSTCHAN", (sub_ch - 1) | 1024)
end

-- the plugin, last in the master chain
local fx = find_fx(master, "E4L Sub Out")
if fx < 0 then
  for _, name in ipairs({ "JS:E4L/E4L Sub Out.jsfx", "E4L/E4L Sub Out.jsfx",
                          "JS: E4L Sub Out (sum of the master to a subwoofer output)" }) do
    fx = reaper.TrackFX_AddByName(master, name, false, -1)
    if fx >= 0 then break end
  end
end
if fx < 0 then
  reaper.ShowMessageBox("Could not load E4L Sub Out.jsfx\nCopy the Effects/E4L folder into the REAPER resource folder.", "E4L", 0)
else
  set_param(master, fx, "Sub Output (channel)", sub_ch)
end

-- no double feed from the decoders
for t = 0, reaper.CountTracks(0) - 1 do
  local tr = reaper.GetTrack(0, t)
  for i = 0, reaper.TrackFX_GetCount(tr) - 1 do
    local _, name = reaper.TrackFX_GetFXName(tr, i, "")
    if name:find("E4L Master Bus", 1, true) then set_param(tr, i, "Sub Output (channel, 0 = off)", 0) end
  end
end

reaper.Undo_EndBlock("E4L: add sub to master", -1)
if E4L_SUB_QUIET == nil and fx >= 0 then
  reaper.ShowMessageBox("Sub listo: todo lo que llega al master sale tambien por la salida " .. sub_ch ..
    ".\nAjusta el nivel y el filtro en el plugin E4L Sub Out del master.", "E4L", 0)
end
