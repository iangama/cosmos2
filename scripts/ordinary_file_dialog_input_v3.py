"""Choose/cancel a real Windows file dialog; inspect handles, type with ordinary keys."""
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import time
from PIL import ImageGrab
from ordinary_option_input_v3 import OptionInput
from ordinary_native_input_v9 import user

user.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
user.GetDlgItem.argtypes=[w.HWND,ctypes.c_int]
user.GetDlgItem.restype=w.HWND
user.IsWindowVisible.argtypes=[w.HWND]
user.IsWindowEnabled.argtypes=[w.HWND]


def window_text(hwnd,method):
    value=ctypes.create_unicode_buffer(1024)
    getattr(user,method)(hwnd,value,len(value))
    return value.value


class FileDialogInput(OptionInput):
    def dialog(self):
        self.assert_foreground()
        hwnd=user.GetForegroundWindow()
        kind=window_text(hwnd,'GetClassNameW')
        assert kind=='#32770', 'Expected a Windows file dialog, got '+kind
        return hwnd

    def open_file_dialog(self,selector):
        self.click(selector)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            self.assert_foreground()
            hwnd=user.GetForegroundWindow()
            cancel=user.GetDlgItem(hwnd,2) if window_text(hwnd,'GetClassNameW')=='#32770' else None
            if cancel and user.IsWindowVisible(hwnd) and user.IsWindowVisible(cancel) and user.IsWindowEnabled(cancel):
                time.sleep(.4)  # Wait for the native dialog's first layout and paint.
                self.actions.append(dict(input='Windows file dialog',action='opened',title=window_text(hwnd,'GetWindowTextW')))
                return hwnd
            time.sleep(.1)
        raise TimeoutError('The ordinary file button did not open a Windows dialog')

    def capture_dialog(self,destination):
        hwnd=self.dialog();rect=w.RECT()
        assert user.GetWindowRect(hwnd,ctypes.byref(rect))
        ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom),all_screens=True).save(destination)
        return dict(path=str(destination),method='Unedited Windows file-dialog capture without focus changes',size=[rect.right-rect.left,rect.bottom-rect.top])

    def click_dialog_button(self,identifier):
        dialog=self.dialog();button=user.GetDlgItem(dialog,identifier)
        assert button and user.IsWindowVisible(button) and user.IsWindowEnabled(button)
        rect=w.RECT();assert user.GetWindowRect(button,ctypes.byref(rect))
        x,y=(rect.left+rect.right)//2,(rect.top+rect.bottom)//2
        user.SetCursorPos(x,y);time.sleep(.2)
        user.mouse_event(2,0,0,0,0);time.sleep(.035);user.mouse_event(4,0,0,0,0)
        self.actions.append(dict(input='Windows mouse',action='click native dialog button',label=window_text(button,'GetWindowTextW'),x=x,y=y))

    def cancel_file_dialog(self):
        self.click_dialog_button(2)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if user.GetForegroundWindow()==self.hwnd:return
            time.sleep(.1)
        raise TimeoutError('The Windows file dialog did not cancel and return to Cosmos2')

    def choose_file(self,selector,path,dialog_capture=None):
        path=Path(path).resolve()
        assert path.is_file() and path.suffix=='.json' and path.stat().st_size<=16*1024*1024
        self.open_file_dialog(selector)
        if dialog_capture:self.capture_dialog(dialog_capture)
        # File name / Nome: both common Windows localizations use Alt+N.
        self.key(78,alt=True);self.key(65,ctrl=True);self.type_text(str(path));time.sleep(.2);self.click_dialog_button(1)
        self.page.wait_for_function('document.querySelector('+__import__('json').dumps(selector)+').files[0]?.name==='+__import__('json').dumps(path.name),timeout=15000)
        self.assert_foreground()
        assert user.GetForegroundWindow()==self.hwnd
        self.actions.append(dict(input='Windows file dialog',action='chose existing file',file_name=path.name))
