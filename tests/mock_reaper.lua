-- minimal REAPER API mock for testing the E4L scripts
local T = {}               -- tracks (array)
local master = {name="MASTER", vals={I_NCHAN=2}, fx={}, sends={[0]={},[1]={{dst=nil,vals={I_SRCCHAN=0,I_DSTCHAN=0}}}}}
local FXP = MOCK_FXP or {
  ["E4L Master Bus.jsfx"]={"Decoder","Order Weighting","Ambisonics Order","Input Gain (dB)","Output Gain (dB)","Sub Output (channel, 0 = off)","Sub Level (dB)","Sub Low-pass (Hz, 0 = off)"},
  ["E4L Looper.jsfx"]={"Length (bars)","Record","Play","Overdub","Clear","Loop Volume (dB)","Input Thru (live input also to the output)","Recording Latency Compensation (ms)","-Status (0 empty 1 armed 2 rec 3 play 4 stop)","-Pending (1 play 2 stop)","-Loop Bars","-Loop Start (QN)","-Loop Length (QN)"},
  ["E4L Sub Out.jsfx"]={"Sub Output (channel)","Sum of","Sub Level (dB)","Sub Low-pass (Hz, 0 = off)","Sub"},
  ["E4L Mono Panner.jsfx"]={"Azimuth","Elevation","Radius","Range","-Current Azimuth","-Current Elevation"},
  ["E4L Stereo Panner.jsfx"]={"Azimuth","Elevation","Radius","Range","-Current Azimuth","-Current Elevation"},
}
local function newtr() return {name="", vals={I_NCHAN=2,B_MAINSEND=1}, fx={}, sends={[0]={},[1]={}}} end
reaper = {}
function reaper.CountTracks() return #T end
function reaper.GetTrack(_, i) return T[i+1] end
function reaper.GetMasterTrack() return master end
function reaper.InsertTrackAtIndex(i) table.insert(T, i+1, newtr()) end
function reaper.GetSetMediaTrackInfo_String(tr, k, v, set)
  if k == "P_NAME" then if set then tr.name = v end return true, tr.name end
  tr.ext = tr.ext or {}
  if set then tr.ext[k] = v end
  return true, tr.ext[k] or ""
end
function reaper.SetMediaTrackInfo_Value(tr, k, v) tr.vals[k]=v end
function reaper.GetMediaTrackInfo_Value(tr, k)
  if k=="IP_TRACKNUMBER" then for i,t in ipairs(T) do if t==tr then return i end end end
  return tr.vals[k] or 0 end
function reaper.TrackFX_AddByName(tr, name)
  local file = name:match("E4L/(.+)$"); if not file or not FXP[file] then return -1 end
  table.insert(tr.fx, {file=file, name="JS: "..file:gsub("%.jsfx$",""), p={}}); return #tr.fx-1 end
function reaper.TrackFX_GetCount(tr) return #tr.fx end
function reaper.TrackFX_Delete(tr, i) table.remove(tr.fx, i + 1) return true end
function reaper.TrackFX_GetFXName(tr, i) return true, tr.fx[i+1].name end
function reaper.TrackFX_GetNumParams(tr, i) return #FXP[tr.fx[i+1].file] end
function reaper.TrackFX_GetParamName(tr, i, p) return true, FXP[tr.fx[i+1].file][p+1] end
function reaper.TrackFX_SetParam(tr, i, p, v) tr.fx[i+1].p[FXP[tr.fx[i+1].file][p+1]]=v return true end
function reaper.TrackFX_GetParam(tr, i, p) return tr.fx[i+1].p[FXP[tr.fx[i+1].file][p+1]] or 0 end
function reaper.CreateTrackSend(src, dst) local c = dst and 0 or 1; table.insert(src.sends[c], {dst=dst, vals={}}); return #src.sends[c]-1 end
function reaper.GetTrackNumSends(tr, c) return #tr.sends[c] end
function reaper.SetTrackSendInfo_Value(tr, c, i, k, v) tr.sends[c][i+1].vals[k]=v return true end
function reaper.GetTrackSendInfo_Value(tr, c, i, k) if k=="P_DESTTRACK" then return tr.sends[c][i+1].dst end return tr.sends[c][i+1].vals[k] or 0 end
function reaper.GetUserInputs(t, n, cap, def) return true, MOCK_INPUT or def end
function reaper.GetInputOutputLatency() return 256, 256 end
function reaper.GetAudioDeviceInfo(k) return true, "48000" end
function reaper.ShowMessageBox(s) MOCK_MSG = s end
function reaper.Undo_BeginBlock() end
function reaper.Undo_EndBlock() end
function reaper.PreventUIRefresh() end
function reaper.TrackList_AdjustWindows() end
function reaper.CountSelectedTracks() return 0 end
-- transport / UI helpers for the Live Panel
MOCK_PLAY = 1; MOCK_POS = 10.0; MOCK_SEL = nil; MOCK_CMDS = {}; MOCK_DEFER = nil; MOCK_EXT = {}
function reaper.GetPlayState() return MOCK_PLAY end
function reaper.GetPlayPosition() return MOCK_POS end
function reaper.GetCursorPosition() return 0 end
function reaper.TimeMap2_timeToBeats(_, t) local q = t * 2; return q % 4, math.floor(q / 4), 4, q, 4 end
function reaper.TimeMap_GetTimeSigAtTime() return 4, 4, 120 end
function reaper.TimeMap2_timeToQN(_, t) return t * 2 end
function reaper.Master_GetTempo() return 120 end
function reaper.IsTrackSelected(tr) return MOCK_SEL == tr end
function reaper.SetOnlyTrackSelected(tr) MOCK_SEL = tr end
function reaper.TrackFX_Show() end
function reaper.Main_OnCommand(c) MOCK_CMDS[#MOCK_CMDS + 1] = c end
function reaper.time_precise() return os.clock() end
function reaper.defer(f) MOCK_DEFER = f end
function reaper.SetExtState(a, b, v) MOCK_EXT[a .. b] = v end
function reaper.GetExtState(a, b) return MOCK_EXT[a .. b] or "" end
MOCK_KEY = 0
gfx = { w = 1240, h = 560, x = 0, y = 0, mouse_x = 0, mouse_y = 0, mouse_cap = 0 }
function gfx.init() end
function gfx.set() end
function gfx.rect() end
function gfx.line() end
function gfx.circle() end
function gfx.setfont() end
function gfx.measurestr(s) return #s * 7, 14 end
MOCK_TEXT = {}
function gfx.drawstr(s) MOCK_TEXT[#MOCK_TEXT + 1] = tostring(s) end
function status_text_for_test() local t = table.concat(MOCK_TEXT, '\n'); MOCK_TEXT = {}; return t end
function gfx.update() end
function gfx.quit() end
function gfx.dock() return 0 end
function gfx.showmenu() return 0 end
function gfx.getchar() local k = MOCK_KEY; MOCK_KEY = 0; return k end

-- project ext state, items, files, projects (live scripts)
MOCK_PROJEXT = {}
function reaper.GetProjExtState(_, a, b) local v = MOCK_PROJEXT[a .. b]; if v then return 1, v end return 0, "" end
function reaper.SetProjExtState(_, a, b, v) MOCK_PROJEXT[a .. b] = v return 1 end
MOCK_CURSOR = 0; MOCK_SRCLEN = 7.9; MOCK_FILES = {}; MOCK_SAVED = {}; MOCK_OPENED = {}
function reaper.SetEditCurPos(t) MOCK_CURSOR = t end
function reaper.InsertMedia(file)
  local tr = MOCK_SEL
  tr.items = tr.items or {}
  local item = { file = file, vals = { D_POSITION = MOCK_CURSOR, D_LENGTH = MOCK_SRCLEN }, take = { vals = { D_PLAYRATE = 1 } } }
  item.take.item = item
  table.insert(tr.items, item)
  return 1
end
MOCK_INSERTMEDIA_USED = false
local _insert = reaper.InsertMedia
function reaper.InsertMedia(...) MOCK_INSERTMEDIA_USED = true; return _insert(...) end
function reaper.PCM_Source_CreateFromFile(file)
  if file:match("broken") then return nil end
  return { file = file }
end
function reaper.PCM_Source_Destroy() end
function reaper.AddMediaItemToTrack(tr)
  tr.items = tr.items or {}
  local item = { vals = { D_POSITION = 0, D_LENGTH = 0 } }
  table.insert(tr.items, item)
  return item
end
function reaper.AddTakeToMediaItem(item)
  item.take = { vals = { D_PLAYRATE = 1 }, item = item }
  return item.take
end
function reaper.SetMediaItemTake_Source(take, src) take.item.file = src.file; take.src = src end
function reaper.GetSetMediaItemTakeInfo_String(take, k, v) take.vals[k] = v return true, v end
function reaper.UpdateItemInProject() end
MOCK_PLAYBTN = 0
function reaper.OnPlayButton() MOCK_PLAYBTN = MOCK_PLAYBTN + 1; MOCK_PLAY = 1 end
function reaper.CountTrackMediaItems(tr) return tr.items and #tr.items or 0 end
function reaper.GetTrackMediaItem(tr, i) return tr.items[i + 1] end
function reaper.GetActiveTake(item) return item.take end
function reaper.GetMediaItemTake_Source(take) return take end
function reaper.GetMediaSourceLength() return MOCK_SRCLEN, false end
function reaper.SetMediaItemTakeInfo_Value(take, k, v) take.vals[k] = v return true end
function reaper.SetMediaItemInfo_Value(item, k, v) item.vals[k] = v return true end
function reaper.GetMediaItemInfo_Value(item, k) return item.vals[k] or 0 end
function reaper.GetResourcePath() return "/res" end
function reaper.RecursiveCreateDirectory() return 1 end
function reaper.EnumerateFiles(_, i) return MOCK_FILES[i + 1] end
function reaper.Main_SaveProjectEx(_, path) MOCK_SAVED[#MOCK_SAVED + 1] = path end
function reaper.Main_openProject(path) MOCK_OPENED[#MOCK_OPENED + 1] = path end
function reaper.GetProjectName() return "" end
function reaper.GetUserFileNameForRead() return true, "/sounds/pad.wav" end
function reaper.SetMediaTrackInfo_Value_orig() end
local _cmd = reaper.Main_OnCommand
function reaper.Main_OnCommand(c, f)
  if c == 40023 then           -- File: New project
    for i = #T, 1, -1 do T[i] = nil end
    master.fx = {}; master.sends = {[0]={},[1]={{dst=nil,vals={I_SRCCHAN=0,I_DSTCHAN=0}}}}; master.vals = {I_NCHAN=2}
    MOCK_PROJEXT = {}
  end
  _cmd(c, f)
end

function reaper.Track_GetPeakInfo() return 0.25 end

MOCK = {T=T, master=master}
