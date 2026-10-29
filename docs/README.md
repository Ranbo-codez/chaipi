# ChAIpi docs

Start here:

| Doc | What's in it |
|---|---|
| [Parts list](parts-list.md) | Everything to buy for one ChAIpi, with quantities and the tools you need |
| [12 — Hardware](12-revision-3.md) | The pitfalls of each part, the final pin map, power, audio, how Transfer works |
| [03 — Wiring](03-wiring.md) | Step-by-step wiring with a test after each step, every wire in one table, troubleshooting |
| [The complete circuit](wiring/circuit.svg) | Every part and every wire on one page |
| [The cases](../enclosure/case/README.md) | Three 3D-printed shapes with the same parts inside: the [clamshell](../enclosure/case/README.md), the Game Boy-style [portrait](../enclosure/case-portrait/README.md) case and the [landscape](../enclosure/case-landscape/README.md) handheld. Print files, screws, assembly, editing in Tinkercad |
| [13 — Device software](13-device-software.md) | How the OS runs on the Pi, processes, hooks, folders, what's been tested, the bring-up plan |
| [../image/README.md](../image/README.md) | Getting the SD card: download, build it yourself, or install over SSH |
| [../device/README.md](../device/README.md) | Code map and the tests |
| [../enclosure/logo-badge/README.md](../enclosure/logo-badge/README.md) | The 3D-printable logo badge |

Diagrams: [wiring/circuit.svg](wiring/circuit.svg) (the whole circuit), [wiring/header-map.svg](wiring/header-map.svg) (which pin goes where) and [wiring/power.svg](wiring/power.svg) (battery to 5 V). [wiring/tools/make_circuit.py](wiring/tools/make_circuit.py) draws the first, [wiring/tools/make_diagrams.py](wiring/tools/make_diagrams.py) the other two.

## Design history
[history/](history/README.md) has the original plan (an OLED, a 5-way joystick and voice input) and revision 2. They're kept to show how the design got here. Where they disagree with the docs above, the docs above win.
