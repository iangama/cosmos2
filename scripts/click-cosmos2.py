"""Send one client-area click only to the recorded Cosmos2 native window."""
import argparse
import ctypes
import json
from pathlib import Path
import time

parser = argparse.ArgumentParser()
parser.add_argument('x', type=int)
parser.add_argument('y', type=int)
parser.add_argument('--wheel', type=int, default=0, help='Scroll ticks; positive up, negative down.')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
pid = json.loads((root/'output/session.json').read_text(encoding='utf-8-sig'))['app']
user = ctypes.windll.user32
windows = []
callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
@callback
def collect(handle, _):
    owner = ctypes.c_ulong()
    user.GetWindowThreadProcessId(ctypes.c_void_p(handle), ctypes.byref(owner))
    if owner.value == pid and user.IsWindowVisible(ctypes.c_void_p(handle)):
        windows.append(handle)
    return True
user.EnumWindows(collect, 0)
if not windows:
    raise RuntimeError('Cosmos2 native window missing')
handle = ctypes.c_void_p(windows[0])
class Rect(ctypes.Structure):
    _fields_ = [(k, ctypes.c_long) for k in ('left','top','right','bottom')]
rect = Rect()
user.GetClientRect(handle, ctypes.byref(rect))
if not (0 <= args.x < rect.right and 0 <= args.y < rect.bottom):
    raise ValueError('Click outside Cosmos2 client area')
point = args.x + (args.y << 16)
user.PostMessageW(handle, 0x200, 0, point)
if args.wheel:
    if abs(args.wheel) > 24:
        raise ValueError('Scroll request too large')
    class Point(ctypes.Structure):
        _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]
    screen = Point(args.x, args.y)
    user.ClientToScreen(handle, ctypes.byref(screen))
    user.PostMessageW(handle, 0x20A, ((120*args.wheel) & 0xffff) << 16,
                      (screen.x & 0xffff) | ((screen.y & 0xffff) << 16))
else:
    user.PostMessageW(handle, 0x201, 1, point)
    time.sleep(.05)
    user.PostMessageW(handle, 0x202, 0, point)
time.sleep(.7)
print(json.dumps({'pid':pid,'client_position':[args.x,args.y],'wheel_ticks':args.wheel}))
