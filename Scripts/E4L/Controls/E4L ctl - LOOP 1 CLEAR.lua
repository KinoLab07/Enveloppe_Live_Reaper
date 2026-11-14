-- E4L control action: LOOP 1 CLEAR
-- Bind it to a MIDI button: Actions > Show action list > select it > Add... > press the button.
local dir = debug.getinfo(1, "S").source:match("@?(.*[/\\])") or ""
dofile(dir .. "../e4l_control.lua").run(debug.getinfo(1, "S").source:match("@?(.*)"))
