"""Ordinary Windows mouse/keyboard input; CDP is used only for reading DOM state."""
from pathlib import Path
import ctypes
from ctypes import wintypes as w
import json
import time

from PIL import ImageGrab
import psutil

ROOT = Path(__file__).resolve().parents[1]
user = ctypes.WinDLL('user32', use_last_error=True)
try:
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except (AttributeError, OSError):
    user.SetProcessDPIAware()
CALLBACK = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
user.EnumWindows.argtypes = [CALLBACK, w.LPARAM]
user.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user.GetClientRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
user.ClientToScreen.argtypes = [w.HWND, ctypes.POINTER(w.POINT)]
user.GetForegroundWindow.restype = w.HWND
user.SetForegroundWindow.argtypes = [w.HWND]
user.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user.mouse_event.argtypes = [w.DWORD, w.DWORD, w.DWORD, w.DWORD, ctypes.c_size_t]
user.keybd_event.argtypes = [w.BYTE, w.BYTE, w.DWORD, ctypes.c_size_t]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', w.WORD), ('wScan', w.WORD), ('dwFlags', w.DWORD),
                ('time', w.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', w.LONG), ('dy', w.LONG), ('mouseData', w.DWORD),
                ('dwFlags', w.DWORD), ('time', w.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', w.DWORD), ('wParamL', w.WORD), ('wParamH', w.WORD)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ('u',)
    _fields_ = [('type', w.DWORD), ('u', INPUTUNION)]


user.SendInput.argtypes = [w.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user.SendInput.restype = w.UINT


class NativeInput:
    def __init__(self, pid, page=None):
        self.pid, self.page, self.actions = pid, page, []
        matches = []
        @CALLBACK
        def each(hwnd, _):
            owner = w.DWORD()
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and user.IsWindowVisible(hwnd):
                rect = w.RECT()
                if user.GetClientRect(hwnd, ctypes.byref(rect)) and rect.right > 300 and rect.bottom > 200:
                    matches.append(hwnd)
            return True
        user.EnumWindows(each, 0)
        assert len(matches) == 1, 'Expected one visible Cosmos2 application window'
        self.hwnd = matches[0]
        self.focus()

    def focus(self):
        user.ShowWindow(self.hwnd, 9)
        user.SetForegroundWindow(self.hwnd)
        time.sleep(.08)
        self.assert_foreground()

    def assert_foreground(self):
        hwnd = user.GetForegroundWindow()
        pid = w.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != self.pid:
            ancestors = {p.pid for p in psutil.Process(pid.value).parents()}
            assert self.pid in ancestors, 'Input refused: foreground is not Cosmos2 or its owned dialog'

    def bounds(self):
        rect, origin = w.RECT(), w.POINT(0, 0)
        assert user.GetClientRect(self.hwnd, ctypes.byref(rect))
        assert user.ClientToScreen(self.hwnd, ctypes.byref(origin))
        return origin.x, origin.y, rect.right, rect.bottom

    def click_at(self, x, y, label='visible point'):
        self.focus()
        left, top, width, height = self.bounds()
        assert 0 <= x < width and 0 <= y < height, (label, x, y, width, height)
        assert user.SetCursorPos(round(left+x), round(top+y))
        time.sleep(.2)  # Let GLFW/CEF consume the genuine cursor movement before pressing.
        user.mouse_event(2, 0, 0, 0, 0)
        time.sleep(.035)
        user.mouse_event(4, 0, 0, 0, 0)
        self.actions.append(dict(input='Windows mouse', action='click', target=label, x=round(x), y=round(y)))
        time.sleep(.08)

    def key(self, code, *, ctrl=False, alt=False):
        self.assert_foreground()
        extended_keys = {33, 34, 35, 36, 37, 38, 39, 40, 45, 46, 91, 92, 111, 144}
        def emit(value, released=False):
            scan = user.MapVirtualKeyW(value, 0)
            flags = (1 if value in extended_keys else 0) | (2 if released else 0)
            user.keybd_event(value, scan, flags, 0)
        modifiers = ([17] if ctrl else []) + ([18] if alt else [])
        for value in modifiers:
            emit(value)
        emit(code)
        time.sleep(.03)
        emit(code, True)
        for value in reversed(modifiers):
            emit(value, True)
        self.actions.append(dict(input='Windows keyboard', key=code, ctrl=ctrl, alt=alt,
                                 scancode=user.MapVirtualKeyW(code, 0), extended=code in extended_keys))
        time.sleep(.06)

    def type_text(self, value):
        self.assert_foreground()
        encoded = value.encode('utf-16-le')
        for index in range(0, len(encoded), 2):
            scan = int.from_bytes(encoded[index:index+2], 'little')
            events = (INPUT*2)()
            for event, flags in zip(events, [4, 6]):
                event.type = 1
                event.ki = KEYBDINPUT(0, scan, flags, 0, 0)
            assert user.SendInput(2, events, ctypes.sizeof(INPUT)) == 2
        self.actions.append(dict(input='Windows keyboard', action='type', characters=len(value)))

    def capture(self, destination):
        self.focus()
        left, top, width, height = self.bounds()
        ImageGrab.grab(bbox=(left, top, left+width, top+height), all_screens=True).save(destination)
        return dict(path=str(destination), size=[width, height], method='Unedited Windows client-area capture')

    def click(self, selector):
        assert self.page is not None
        # All evaluations in this class are read-only. Scrolling uses the OS wheel.
        expression='''(()=>{const e=document.querySelector(SELECTOR);if(!e)return null;
          const r=e.getBoundingClientRect(),z=Number(getComputedStyle(document.body).zoom)||1;
          const b=document.body.getBoundingClientRect(),layout=parseFloat(getComputedStyle(document.body).width);
          const factor=Math.abs(b.width/layout-1)<.02?z:1;
          let clip={left:0,top:0,right:innerWidth/factor,bottom:innerHeight/factor};
          for(let p=e.parentElement;p;p=p.parentElement){const s=getComputedStyle(p);
            if(/auto|scroll|hidden/.test(s.overflowY)&&p.scrollHeight>p.clientHeight){const q=p.getBoundingClientRect();clip={left:Math.max(clip.left,q.left),top:Math.max(clip.top,q.top),right:Math.min(clip.right,q.right),bottom:Math.min(clip.bottom,q.bottom)};}}
          const hit=document.elementFromPoint((r.left+r.right)/2*factor,(r.top+r.bottom)/2*factor);
          return {x:(r.left+r.right)/2,y:(r.top+r.bottom)/2,width:r.width,height:r.height,clip,factor,vw:innerWidth,vh:innerHeight,disabled:e.matches(':disabled'),display:getComputedStyle(e).display,hitTarget:hit===e||e.contains(hit),hit:hit?.id||hit?.tagName};})()'''.replace('SELECTOR', json.dumps(selector))
        for attempt in range(24):
            row = self.page.evaluate(expression)
            assert row and row['width'] > 0 and row['height'] > 0 and not row['disabled'], (selector, row)
            clip = row['clip']
            if clip['top']+5 <= row['y'] <= clip['bottom']-5 and clip['left'] <= row['x'] <= clip['right'] and row['hitTarget']:
                _, _, width, height = self.bounds()
                return self.click_at(row['x']*row['factor']*width/row['vw'],
                                     row['y']*row['factor']*height/row['vh'], selector)
            assert clip['top'] < clip['bottom'], 'Control is inside a collapsed or clipped panel: '+selector
            self.focus()
            left, top, width, height = self.bounds()
            user.SetCursorPos(round(left+(clip['left']+clip['right'])/2*row['factor']*width/row['vw']),
                              round(top+(clip['top']+clip['bottom'])/2*row['factor']*height/row['vh']))
            time.sleep(.2)
            visible = clip['top']+5 <= row['y'] <= clip['bottom']-5
            if visible and not row['hitTarget']:
                delta = 120 if row['y'] < (clip['top']+clip['bottom'])/2 else -120
            else:
                delta = 360 if row['y'] < clip['top'] else -360
            user.mouse_event(0x0800, 0, 0, delta & 0xffffffff, 0)
            self.actions.append(dict(input='Windows mouse', action='wheel', delta=delta, target=selector))
            time.sleep(.08)
        raise RuntimeError('Control could not be reached with ordinary scrolling: '+selector)

    def fill(self, selector, value):
        self.click(selector)
        self.page.wait_for_function('document.activeElement===document.querySelector('+json.dumps(selector)+')', timeout=2000)
        self.key(65, ctrl=True)
        self.type_text(str(value))

    def select(self, selector, value):
        values = self.page.evaluate('[...document.querySelector('+json.dumps(selector)+').options].map(o=>o.value)')
        index = values.index(value)
        self.click(selector)
        self.key(36)
        for _ in range(index):
            self.key(40)
        self.key(13)
        self.page.wait_for_function('document.querySelector('+json.dumps(selector)+').value==='+json.dumps(value))
