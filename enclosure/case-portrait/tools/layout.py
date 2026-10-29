"""ChAIpi portrait case (Game Boy style): every position in one place.

    python3 enclosure/case-portrait/tools/layout.py      # collision and clearance check

Coordinates in mm: X left to right, Y from the bottom edge (nearest you) up to the top, Z from
the back (0) to the face. Part sizes and the shared maths are in enclosure/tools/slab.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import slab  # noqa: E402

BIG, SMALL = 10.5, 8.5          # button cap diameters (the small keys sit 13.6 mm apart, like the clamshell's grid)

LAYOUT = slab.Layout(
    name='portrait',
    title='ChAIpi portrait case',
    W=100.0, D=148.0,
    radii=(6.0, 24.0, 4.0, 4.0),            # bottom-left, bottom-right (the big classic curve), top-right, top-left
    picture_c=(50.0, 108.0),                # the picture is centred left to right
    joy_c=(26.0, 47.0),                     # the stick, where a D-pad would be
    buttons={
        'Undo':    ((68.0, 40.0), BIG),     # "B"
        'Confirm': ((84.0, 51.0), BIG),     # "A"
        'Fn':      ((29.6, 17.0), SMALL),   # the bottom row, where Select and Start would be
        'Tab':     ((43.2, 17.0), SMALL),
        'Menu':    ((56.8, 17.0), SMALL),
        'Esc':     ((70.4, 17.0), SMALL),
    },
    carriers=[
        dict(name='face_buttons', buttons=['Undo', 'Confirm'], screws=[(61.5, 53.5), (75.5, 60.5)]),
        dict(name='small_keys', buttons=['Fn', 'Tab', 'Menu', 'Esc'], screws=[(19.5, 17.0), (80.5, 17.0)]),
    ],
    battery=(39.7, 62.0, 'L'),              # under the A/B keys and the bottom of the screen; wires out to the left
    pi=(30.0, 100.0),                       # under the screen, upside down over the back vents
    boards={
        'rtc':   (58.0, 34.0, False),       # under the A/B keys
        'boost': (56.9, 10.0, False, 'L'),  # under the grille; trimmer at the left end
        'chg':   (8.5, 4.0, False),         # bottom-left, next to the USB-C breakout
        'adc':   (8.6, 58.0, True),         # left of the battery, next to the joystick
    },
    usbc_x=43.4,                            # port in the middle of the bottom edge
    # face screws: no post may hang over a part, or that part couldn't be put in
    screws=[(5.0, 5.0, 'LB'), (80.0, 5.2, 'B'), (95.0, 143.0, 'RT'), (5.0, 143.0, 'LT'),
            (4.8, 74.0, 'L'), (95.2, 74.0, 'R')],
    wordmark=('ChAIpi', 7.5, 50.0, 66.0),   # under the screen
    back_wordmark=('ChAIpi', 12.0, 50.0, 50.0),
    lens=dict(x0=13.5, y0=75.9, x1=86.5, y1=136.6, r=2.5, r_br=12.0),   # dark surround, big curve bottom-right
    grille=tuple(((86.0 + (i - 2) * 2.77 - 3.0, 28.0 - (i - 2) * 1.6 - 5.2),
                  (86.0 + (i - 2) * 2.77 + 3.0, 28.0 - (i - 2) * 1.6 + 5.2), 1.6) for i in range(5)),
)

if __name__ == '__main__':
    LAYOUT.report()
