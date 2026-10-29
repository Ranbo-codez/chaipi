# Changelog

## Unreleased
- A slim clamshell case (enclosure/case): print-ready STL files, rough models of every part, a fit test, and a guide for printing, assembly and editing in Tinkercad. The hinge pivots on two M2.5 screws. A script checks that nothing collides and that the lid swings freely.
- The finished case as 19 separate files (enclosure/case/stl/assembled) that land already put together when imported into one Tinkercad design.
- Two more case shapes with the same parts and screw kit: a Game Boy-style portrait case (enclosure/case-portrait) and a wide landscape case (enclosure/case-landscape). The Pi lies upside down over vent slots in the back. One shared script (enclosure/tools) builds both, with the same collision checks, Tinkercad files and renders. Not printed yet.
- The complete circuit on one page (docs/wiring/circuit.svg).
- USB data for drive mode now goes to the Pi's USB_DP / USB_DM test pads inside the case.

## 1.0.0 (revision 3), first public release
Not yet tested on real hardware.

- The ChAIpi OS for a 2.8" ILI9341 screen, a joystick and six buttons: Play (400–3190 Elo), Helper, Two player, History with one PGN file per game, and game review.
- Extras: eight games, six tools, puzzles, coordinate training, YouTube Shorts, and your own Python apps through the `chaipi` SDK.
- Transfer over ChAIpi's own Wi-Fi with a phone page and a PIN, plus USB drive mode and the microSD slot. Backup and restore.
- The device host: Node.js + Skia on the framebuffer, Stockfish 19 over UCI, GPIO and ADC input, NetworkManager, the USB gadget.
- An SD-card image built by GitHub Actions (Raspberry Pi OS Lite 64-bit, Debian 13), with no SSH key inside. Wi-Fi, time zone and SSH keys can be set from files on the boot partition.
- The emulator: the same OS in any browser, as a single offline file and (once the repository is public) a website.
- A parts list, a step-by-step wiring guide with diagrams, and a 3D-printable logo badge.
