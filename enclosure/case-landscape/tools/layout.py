"""ChAIpi landscape case: every position in one place.

    python3 enclosure/case-landscape/tools/layout.py     # collision and clearance check

Coordinates in mm: X left to right, Y from the bottom edge (nearest you) up to the top, Z from
the back (0) to the face. Part sizes and the shared maths are in enclosure/tools/slab.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import slab  # noqa: E402

BIG, SMALL = 10.5, 8.5          # button cap diameters
DX, DY, STEP = 158.2, 42.0, 12.5  # the button diamond: centre and spacing

LAYOUT = slab.Layout(
    name='landscape',
    title='ChAIpi landscape case',
    W=180.0, D=76.0,
    radii=(16.0, 16.0, 16.0, 16.0),
    picture_c=(90.0, 38.0),                 # the picture is centred
    joy_c=(26.0, 50.0),                     # left thumb
    buttons={
        'Confirm': ((DX + STEP, DY), BIG),  # right thumb: a diamond
        'Undo':    ((DX, DY - STEP), BIG),
        'Esc':     ((DX, DY + STEP), SMALL),
        'Fn':      ((DX - STEP, DY), SMALL),
        'Tab':     ((18.0, 18.0), SMALL),   # under the stick
        'Menu':    ((34.0, 18.0), SMALL),
    },
    carriers=[
        dict(name='diamond', buttons=['Confirm', 'Undo', 'Esc', 'Fn'], screws=[(DX + STEP, DY + STEP), (DX - STEP, DY - STEP)]),
        dict(name='left_keys', buttons=['Tab', 'Menu'], screws=[(26.0, 9.0), (26.0, 27.0)]),
    ],
    battery=(60.0, 3.5, 'L'),               # under the bottom half of the screen
    pi=(57.0, 40.5),                        # under the top half of the screen, upside down over the back vents
    boards={
        'rtc':   (140.0, 4.0, True),        # right wing, under the diamond
        'boost': (140.0, 46.0, False, 'L'), # right wing, top; trimmer at the left end
        'chg':   (33.0, 3.0, True),         # left wing, next to the USB-C breakout
        'adc':   (115.0, 9.0, True),        # beside the battery, under the screen
    },
    usbc_x=18.0,                            # port in the bottom edge, under the left thumb
    # four corners, and four along the long edges, placed beside the battery and the Pi rather than over them
    # (a post hanging over a part would stop it going in)
    screws=[(7.8, 7.8, ''), (172.2, 7.8, ''), (172.2, 68.2, ''), (7.8, 68.2, ''),
            (54.0, 4.8, 'B'), (126.0, 4.8, 'B'), (53.2, 71.2, 'T'), (126.0, 71.2, 'T')],
    back_wordmark=('ChAIpi', 12.0, 90.0, 32.0),
    lens=dict(x0=54.2, y0=9.4, x1=125.8, y1=66.6, r=3.0, r_br=3.0),     # dark surround around the screen
)

if __name__ == '__main__':
    LAYOUT.report()
