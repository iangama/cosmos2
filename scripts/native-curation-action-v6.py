"""One reviewable ordinary-input action in the current Cosmos2 window."""
from pathlib import Path
import argparse
import hashlib
import json
import time

import psutil
from ordinary_native_input_v6 import NativeInput

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--click-at', nargs=2, type=float)
    parser.add_argument('--click')
    parser.add_argument('--fill', nargs=2)
    parser.add_argument('--select', nargs=2)
    parser.add_argument('--key', type=int)
    parser.add_argument('--capture')
    parser.add_argument('--close', action='store_true')
    args = parser.parse_args()
    assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / ('output/original-flow-native-' + args.label)
    assert folder.is_dir()
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    process = psutil.Process(session['app'])
    assert process.name().lower() == 'openspace.exe'
    page = None
    if args.click or args.fill or args.select:
        from cef_page_v2 import Page
        page = Page()
    result = dict(actions=[], session_pid=process.pid, observer_only_cdp=True)
    try:
        window = NativeInput(process.pid, page)
        if args.click_at:
            window.click_at(*args.click_at)
        if args.click:
            window.click(args.click)
        if args.fill:
            window.fill(*args.fill)
        if args.select:
            window.select(*args.select)
        if args.key:
            window.key(args.key)
        if args.close:
            window.key(115, alt=True)
            result['app_exit'] = process.wait(timeout=25)
        time.sleep(.25)
        if args.capture:
            assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.capture)
            target = folder / (args.capture + '.png')
            assert not target.exists()
            result['capture'] = window.capture(target)
            result['capture']['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        result['actions'] = window.actions
        if page:
            result['browser'] = page.evaluate('({path:location.pathname,title:document.title,scale:document.getElementById("ui-scale")?.value,notice:document.getElementById("notice")?.textContent,force_status:document.getElementById("force-status")?.textContent,force_error:document.getElementById("force-status")?.classList.contains("error"),spatial_error:document.getElementById("spatial-error")?.textContent,layers_error:document.getElementById("layers-error")?.textContent,mode:typeof appState==="undefined"?null:appState?.mode})')
        with (folder / 'ordinary-actions.jsonl').open('a', encoding='utf8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False)+'\n')
        print(json.dumps(result, ensure_ascii=False))
    finally:
        if page:
            page.__exit__()


if __name__ == '__main__':
    main()
