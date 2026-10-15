-- E4L - Live Panel.lua
-- Envelop for REAPER: one window to play the whole live looper set-up.
--
--   * big bar / beat counter, tempo and time signature, play / stop
--   * one row per track with an "E4L Looper": state, length, REC / PLAY / OVERDUB / CLEAR,
--     loop position with its bars
--   * room view (seen from above) with every loop: drag a dot to move that loop
--
-- Keys: Space = play / stop, 1-9 = REC on loop 1-9, 0 = stop all loops.
-- Right-click the header to dock / undock the panel inside REAPER.
-- GPLv2 or later (same as Envelop for Live).

local TITLE = "E4L Live Panel"
local EXT = "E4L_LivePanel"

---------------------------------------------------------------------------------------
-- helpers
local function strip(n) return (n or ""):gsub("^%-", "") end

local function find_param(tr, fx, prefix)
  for p = 0, reaper.TrackFX_GetNumParams(tr, fx) - 1 do
    local _, n = reaper.TrackFX_GetParamName(tr, fx, p, "")
    if strip(n):sub(1, #prefix) == prefix then return p end
  end
  return -1
end

local function getp(tr, fx, p) if fx < 0 or p < 0 then return 0 end return (reaper.TrackFX_GetParam(tr, fx, p)) end
local function setp(tr, fx, p, v) if fx >= 0 and p >= 0 then reaper.TrackFX_SetParam(tr, fx, p, v) end end

local LENGTHS = { 1, 2, 4, 8, 16, 32 }
local STATE_NAME = { [0] = "EMPTY", "ARMED", "REC", "PLAY", "STOPPED" }

---------------------------------------------------------------------------------------
-- scan the project for loopers (cached, refreshed twice a second)
local loops, last_scan = {}, -1

local function scan()
  local list = {}
  for t = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, t)
    local lfx, pfx = -1, -1
    for i = 0, reaper.TrackFX_GetCount(tr) - 1 do
      local _, name = reaper.TrackFX_GetFXName(tr, i, "")
      if lfx < 0 and name:find("E4L Looper", 1, true) then lfx = i
      elseif pfx < 0 and name:find("E4L", 1, true) and name:find("Panner", 1, true) then pfx = i end
    end
    if lfx >= 0 then
      local _, tname = reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)
      list[#list + 1] = {
        tr = tr, name = tname ~= "" and tname or ("Track " .. (t + 1)), lfx = lfx, pfx = pfx,
        p = {
          len = find_param(tr, lfx, "Length"), rec = find_param(tr, lfx, "Record"),
          play = find_param(tr, lfx, "Play"), odub = find_param(tr, lfx, "Overdub"),
          clear = find_param(tr, lfx, "Clear"), status = find_param(tr, lfx, "Status"),
          pend = find_param(tr, lfx, "Pending"), bars = find_param(tr, lfx, "Loop Bars"),
          start = find_param(tr, lfx, "Loop Start"), qn = find_param(tr, lfx, "Loop Length"),
          az = pfx >= 0 and find_param(tr, pfx, "Azimuth") or -1,
          cur_az = pfx >= 0 and find_param(tr, pfx, "Current Azimuth") or -1,
        },
      }
    end
  end
  loops = list
end

---------------------------------------------------------------------------------------
-- drawing primitives
local function rgb(r, g, b, a) gfx.set(r, g, b, a or 1) end

local function rect(x, y, w, h, fill) gfx.rect(x, y, w, h, fill == nil and 1 or fill) end

local function text(s, x, y, w, h, align)  -- align: 0 left, 1 center
  local tw, th = gfx.measurestr(s)
  gfx.x = (align == 1 and w) and (x + (w - tw) / 2) or x
  gfx.y = h and (y + (h - th) / 2) or y
  gfx.drawstr(s)
end

local mouse_down, mouse_was_down, clicked = false, false, false
local drag = nil

local function hit(x, y, w, h)
  return gfx.mouse_x >= x and gfx.mouse_x < x + w and gfx.mouse_y >= y and gfx.mouse_y < y + h
end

local function button(label, x, y, w, h, on, r, g, b)
  if on then rgb(r, g, b) else rgb(0.22, 0.22, 0.26) end
  rect(x, y, w, h)
  if on then rgb(0.05, 0.05, 0.05) else rgb(0.85, 0.85, 0.9) end
  text(label, x, y, w, h, 1)
  return clicked and hit(x, y, w, h)
end

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
    playing = playing, recording = ps & 4 == 4, bar = math.floor(measure) + 1,
    beat = math.floor(beat_in_bar) + 1, beat_frac = beat_in_bar - math.floor(beat_in_bar),
    bpb = math.floor((beats_per_bar or num or 4) + 0.5), num = num or 4, denom = denom or 4,
    bpm = bpm or reaper.Master_GetTempo(), qn = qn,
  }
end

---------------------------------------------------------------------------------------
local function draw_header(tp, W)
  rgb(0.11, 0.11, 0.14); rect(0, 0, W, 74)

  -- bar . beat
  gfx.setfont(2)
  rgb(tp.playing and 0.35 or 0.7, tp.playing and 0.95 or 0.7, tp.playing and 0.5 or 0.75)
  text(string.format("%d . %d", tp.bar, tp.beat), 14, 6)
  gfx.setfont(1)
  rgb(0.6, 0.6, 0.65)
  text("compás . tiempo", 16, 54)

  -- beats of the current bar
  local bx, bw, gap = 200, 26, 5
  for i = 1, tp.bpb do
    local x = bx + (i - 1) * (bw + gap)
    if tp.playing and i == tp.beat then
      if i == 1 then rgb(1, 0.55, 0.2) else rgb(0.35, 0.95, 0.5) end
    else rgb(0.25, 0.25, 0.3) end
    rect(x, 14, bw, 24)
  end
  -- 4-bar phrase
  local phrase = (tp.bar - 1) % 4 + 1
  for i = 1, 4 do
    if i == phrase then rgb(0.5, 0.75, 1) else rgb(0.25, 0.25, 0.3) end
    rect(bx + (i - 1) * 30, 44, 26, 8)
  end
  rgb(0.6, 0.6, 0.65); text("frase de 4 compases", bx + 128, 41)

  -- tempo, signature, transport
  local rx = math.max(bx + tp.bpb * (bw + gap) + 20, W - 330)
  rgb(0.85, 0.85, 0.9)
  text(string.format("%.1f BPM   %d/%d", tp.bpm, tp.num, tp.denom), rx, 12)
  if button(tp.playing and "STOP" or "PLAY", rx, 36, 80, 28, tp.playing, 0.35, 0.95, 0.5) then
    reaper.Main_OnCommand(40044, 0)              -- Transport: Play/stop
  end
  if button("STOP ALL LOOPS", rx + 90, 36, 140, 28, false) then
    for _, L in ipairs(loops) do setp(L.tr, L.lfx, L.p.play, 0) end
  end
end

local function draw_rows(tp, x0, y0, W, H)
  -- rows shrink when there are many loops, so they all fit in the window
  local rowh = math.max(26, math.min(40, math.floor((H - y0 - 6) / math.max(1, #loops))))
  gfx.setfont(1)
  if #loops == 0 then
    rgb(0.7, 0.7, 0.75)
    text("No hay pistas con E4L Looper. Usa el script \"E4L - Live Looper template\".", x0, y0 + 10)
    return
  end
  for i, L in ipairs(loops) do
    local y = y0 + (i - 1) * rowh
    local st = math.floor(getp(L.tr, L.lfx, L.p.status) + 0.5)
    local pend = math.floor(getp(L.tr, L.lfx, L.p.pend) + 0.5)
    local sel = reaper.IsTrackSelected(L.tr)
    rgb(sel and 0.17 or 0.13, sel and 0.17 or 0.13, sel and 0.21 or 0.16); rect(x0, y, W, rowh - 4)

    -- number + name (click = select the track)
    rgb(0.85, 0.85, 0.9)
    text(string.format("%d  %s", i, L.name), x0 + 8, y, nil, rowh - 4)
    if clicked and hit(x0, y, 150, rowh - 4) then reaper.SetOnlyTrackSelected(L.tr) end

    -- state badge
    local col = { [0] = { 0.4, 0.4, 0.45 }, { 1, 0.6, 0.2 }, { 1, 0.3, 0.3 }, { 0.35, 0.95, 0.5 }, { 0.55, 0.7, 0.9 } }
    local c = col[st] or col[0]
    local blink = (st == 1 or pend > 0) and (math.floor(reaper.time_precise() * 4) % 2 == 0)
    rgb(c[1], c[2], c[3], blink and 0.45 or 1); rect(x0 + 150, y + 6, 78, rowh - 16)
    rgb(0.05, 0.05, 0.05)
    local label = STATE_NAME[st] or "?"
    if pend == 1 then label = "→ PLAY" elseif pend == 2 then label = "→ STOP" end
    text(label, x0 + 150, y + 6, 78, rowh - 16, 1)

    -- length (click to cycle)
    local li = math.floor(getp(L.tr, L.lfx, L.p.len) + 0.5)
    local nl = LENGTHS[li + 1] or 4
    if button(nl .. (nl == 1 and " bar" or " bars"), x0 + 234, y + 6, 66, rowh - 16, false) then
      setp(L.tr, L.lfx, L.p.len, (li + 1) % #LENGTHS)
    end

    -- buttons
    local bx = x0 + 306
    local rec_on = st == 1 or st == 2
    if button("REC", bx, y + 6, 48, rowh - 16, rec_on, 1, 0.3, 0.3) then
      setp(L.tr, L.lfx, L.p.rec, getp(L.tr, L.lfx, L.p.rec) > 0.5 and 0 or 1)
    end
    local play_on = getp(L.tr, L.lfx, L.p.play) > 0.5
    if button("PLAY", bx + 52, y + 6, 52, rowh - 16, play_on, 0.35, 0.95, 0.5) then
      setp(L.tr, L.lfx, L.p.play, play_on and 0 or 1)
    end
    local od = getp(L.tr, L.lfx, L.p.odub) > 0.5
    if button("OVD", bx + 108, y + 6, 44, rowh - 16, od, 1, 0.75, 0.2) then
      setp(L.tr, L.lfx, L.p.odub, od and 0 or 1)
    end
    if button("CLR", bx + 156, y + 6, 40, rowh - 16, false) then setp(L.tr, L.lfx, L.p.clear, 1) end
    if button("FX", bx + 200, y + 6, 34, rowh - 16, false) then reaper.TrackFX_Show(L.tr, L.lfx, 3) end

    -- loop position
    local px, pw = bx + 242, W - (bx - x0) - 250
    if pw > 30 then
      rgb(0.2, 0.2, 0.24); rect(px, y + 10, pw, rowh - 24)
      local bars = getp(L.tr, L.lfx, L.p.bars)
      local lqn = getp(L.tr, L.lfx, L.p.qn)
      if (st == 2 or st == 3) and lqn > 0 and tp.playing then
        local ph = ((tp.qn - getp(L.tr, L.lfx, L.p.start)) / lqn) % 1
        if st == 2 then rgb(1, 0.3, 0.3, 0.9) else rgb(0.35, 0.95, 0.5, 0.9) end
        rect(px, y + 10, pw * ph, rowh - 24)
      end
      rgb(0.5, 0.5, 0.55)
      local nb = math.floor(bars + 0.5)
      for k = 1, nb - 1 do gfx.line(px + pw * k / nb, y + 10, px + pw * k / nb, y + rowh - 15) end
    end
  end
end

local function draw_room(x, y, size)
  local cx, cy, R = x + size / 2, y + size / 2, size / 2 - 22
  rgb(0.11, 0.11, 0.14); rect(x, y, size, size)
  rgb(0.3, 0.3, 0.36); gfx.circle(cx, cy, R, 0, 1)
  gfx.line(cx - R, cy, cx + R, cy); gfx.line(cx, cy - R, cx, cy + R)
  -- speakers (quad)
  for k, a in ipairs({ -45, 45, 135, -135 }) do
    local r = math.rad(a)
    local sx, sy = cx + math.sin(r) * (R + 8), cy - math.cos(r) * (R + 8)
    rgb(0.55, 0.55, 0.6); rect(sx - 7, sy - 7, 14, 14)
    rgb(0.1, 0.1, 0.1); text(tostring(k), sx - 7, sy - 7, 14, 14, 1)
  end
  rgb(0.6, 0.6, 0.65); gfx.circle(cx, cy, 6, 0, 1); gfx.line(cx, cy - 6, cx, cy - 11)
  rgb(0.5, 0.5, 0.55); text("frente", cx - 16, y + 2)

  -- dots
  for i, L in ipairs(loops) do
    if L.pfx >= 0 then
      local az = L.p.cur_az >= 0 and getp(L.tr, L.pfx, L.p.cur_az) or getp(L.tr, L.pfx, L.p.az)
      if drag == i then az = getp(L.tr, L.pfx, L.p.az) end
      local r = math.rad(az)
      local dx, dy = cx + math.sin(r) * R * 0.78, cy - math.cos(r) * R * 0.78
      local st = math.floor(getp(L.tr, L.lfx, L.p.status) + 0.5)
      if st == 3 then rgb(0.35, 0.95, 0.5) elseif st == 2 then rgb(1, 0.3, 0.3)
      else rgb(0.5, 0.5, 0.6) end
      gfx.circle(dx, dy, 11, 1, 1)
      rgb(0.05, 0.05, 0.05); text(tostring(i), dx - 11, dy - 11, 22, 22, 1)
      if clicked and (gfx.mouse_x - dx) ^ 2 + (gfx.mouse_y - dy) ^ 2 < 14 ^ 2 then drag = i end
    end
  end
  -- dragging: azimuth from the mouse angle (0 = front, + = right)
  if drag and mouse_down then
    local L = loops[drag]
    if L and L.pfx >= 0 then
      local az = math.deg(math.atan(gfx.mouse_x - cx, -(gfx.mouse_y - cy)))
      setp(L.tr, L.pfx, L.p.az, math.floor(az + 0.5))
    end
  elseif not mouse_down then drag = nil end
  rgb(0.5, 0.5, 0.55)
  text("arrastra un punto para mover el loop", x + 6, y + size - 16)
end

---------------------------------------------------------------------------------------
local function keyboard(c)
  if c == 32 then reaper.Main_OnCommand(40044, 0) end                   -- space
  if c >= 49 and c <= 57 then                                            -- 1-9: REC
    local L = loops[c - 48]
    if L then setp(L.tr, L.lfx, L.p.rec, getp(L.tr, L.lfx, L.p.rec) > 0.5 and 0 or 1) end
  end
  if c == 48 then for _, L in ipairs(loops) do setp(L.tr, L.lfx, L.p.play, 0) end end  -- 0
end

local function main()
  local c = gfx.getchar()
  if c < 0 then
    reaper.SetExtState(EXT, "dock", tostring(gfx.dock(-1)), true)
    return
  end
  if c == 27 then gfx.quit() return end

  local now = reaper.time_precise()
  if now - last_scan > 0.5 then scan(); last_scan = now end

  mouse_down = gfx.mouse_cap & 1 == 1
  clicked = mouse_down and not mouse_was_down
  if c > 0 then keyboard(c) end

  local W, H = gfx.w, gfx.h
  rgb(0.08, 0.08, 0.1); rect(0, 0, W, H)
  local tp = transport()
  draw_header(tp, W)

  -- right click on the header: dock menu
  if gfx.mouse_cap & 2 == 2 and not RCLICK and gfx.mouse_y < 74 then
    RCLICK = true
    gfx.x, gfx.y = gfx.mouse_x, gfx.mouse_y
    local docked = gfx.dock(-1) & 1 == 1
    local m = gfx.showmenu(docked and "Undock" or "Dock in REAPER")
    if m == 1 then gfx.dock(docked and 0 or 1) end
  elseif gfx.mouse_cap & 2 == 0 then RCLICK = false end

  local room = math.max(0, math.min(H - 90, math.floor(W * 0.36)))
  if W < 760 then room = 0 end
  draw_rows(tp, 8, 84, W - room - 24, H)
  if room > 120 then draw_room(W - room - 8, 84, room) end

  mouse_was_down = mouse_down
  gfx.update()
  reaper.defer(main)
end

local dock = tonumber(reaper.GetExtState(EXT, "dock")) or 0
gfx.init(TITLE, 1100, 520, dock)
gfx.setfont(1, "Arial", 15)
gfx.setfont(2, "Arial", 44, string.byte("b"))
gfx.setfont(1)
scan()
main()
