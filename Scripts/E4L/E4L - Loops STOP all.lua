-- E4L - Loops STOP all.lua
-- Stops every E4L Looper of the project on the next bar. GPLv2 or later.
dofile(debug.getinfo(1, "S").source:match("@?(.*[/\\])") .. "e4l_looper_common.lua")
e4l_for_all_loopers("Play", function() return 0 end, "E4L: stop all loops")
