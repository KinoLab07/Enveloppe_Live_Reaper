-- Shared helpers for the E4L Looper action scripts (not an action itself). GPLv2 or later.

local function looper_fx(track)
  for i = 0, reaper.TrackFX_GetCount(track) - 1 do
    local _, name = reaper.TrackFX_GetFXName(track, i, "")
    if name:find("E4L Looper", 1, true) then return i end
  end
  return -1
end

local function param_index(track, fx, pname)
  for p = 0, reaper.TrackFX_GetNumParams(track, fx) - 1 do
    local _, n = reaper.TrackFX_GetParamName(track, fx, p, "")
    if n == pname then return p end
  end
  return -1
end

local function apply(track, pname, fn)
  local fx = looper_fx(track)
  if fx < 0 then return end
  local p = param_index(track, fx, pname)
  if p < 0 then return end
  local v = reaper.TrackFX_GetParam(track, fx, p)
  reaper.TrackFX_SetParam(track, fx, p, fn(v))
end

function e4l_for_selected_loopers(pname, fn, undo)
  reaper.Undo_BeginBlock()
  for i = 0, reaper.CountSelectedTracks(0) - 1 do apply(reaper.GetSelectedTrack(0, i), pname, fn) end
  reaper.Undo_EndBlock(undo, -1)
end

function e4l_for_all_loopers(pname, fn, undo)
  reaper.Undo_BeginBlock()
  for i = 0, reaper.CountTracks(0) - 1 do apply(reaper.GetTrack(0, i), pname, fn) end
  reaper.Undo_EndBlock(undo, -1)
end
