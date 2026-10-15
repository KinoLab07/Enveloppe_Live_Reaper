-- E4L - Loop PLAY-STOP (selected tracks).lua
-- Toggles PLAY on the E4L Looper of every selected track (starts / stops on the next bar).
-- Assign it to a key or a MIDI button (Actions > Add shortcut). GPLv2 or later.
dofile(debug.getinfo(1, "S").source:match("@?(.*[/\\])") .. "e4l_looper_common.lua")
e4l_for_selected_loopers("Play", function(v) return v > 0.5 and 0 or 1 end, "E4L: loop PLAY/STOP")
