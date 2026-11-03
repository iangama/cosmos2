"""Compare native/canvas150 actual scrolling with captured CEF pixels."""
from pathlib import Path
import hashlib
import json
import subprocess
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'evidence/em-viewport-scroll-diagnostic.json'
assert not DEST.exists()
result={}
with Page() as p:
    p.goto('http://127.0.0.1:4700/')
    p.wait_for_function('typeof appState!=="undefined"&&appState')
    p.locator('#em-lab').click()
    p.wait_for_function('state&&!pending&&nativeState.confirmation?.metadata.time_s===state.time_s',timeout=30000)
    p.locator('#interface-scale').select_option('1.5')
    for mode in ('native','canvas'):
        if p.evaluate('nativeMode')!=(mode=='native'):
            p.locator('#native-toggle').click()
        p.locator('#frame-layers').click()
        p.wait_for_function('!pending')
        result[mode]=p.evaluate('(()=>{const z=Number(getComputedStyle(document.body).zoom);const all=[document.documentElement,document.body,...document.querySelectorAll("main,article,.native-controls,header,.timebar")];return {scroll_y:scrollY,clip_supported:CSS.supports("overflow","clip"),elements:all.map(e=>{const r=e.getBoundingClientRect(),c=getComputedStyle(e);return {tag:e.tagName,cls:e.className,scrollTop:e.scrollTop,scrollHeight:e.scrollHeight,clientHeight:e.clientHeight,top:r.top*z,bottom:r.bottom*z,overflow:c.overflow};})};})()')
        name=f'cosmos2-j-scroll-diagnostic-{mode}-150.png'
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
        result[mode]['screenshot']=name
        result[mode]['screenshot_sha256']=hashlib.sha256((ROOT/'evidence'/name).read_bytes()).hexdigest()
        result[mode]['post_capture_scroll']=p.evaluate('({window:scrollY,html:document.documentElement.scrollTop,body:document.body.scrollTop,article:document.querySelector("article").scrollTop})')
    p.locator('#interface-scale').select_option('1')
    p.locator('#native-return').click()
    p.wait_for_function('location.pathname==="/"')
DEST.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
