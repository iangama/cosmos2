"""Page-level CDP client for OpenSpace CEF; avoids Chrome auto-attach pauses."""
import json
import time
import urllib.request
from websockets.sync.client import connect

class Page:
    def __init__(self):
        targets = json.load(urllib.request.urlopen('http://127.0.0.1:8088/json/list',timeout=3))
        target = next(t for t in targets if t['url'].startswith('http://127.0.0.1:4700'))
        self.ws = connect(target['webSocketDebuggerUrl'],open_timeout=3,close_timeout=.2,ping_interval=None,max_size=64*1024*1024)
        self.serial, self.events, self.handlers = 0, [], {}
        self.call('Runtime.enable');self.call('Network.enable')
    def __enter__(self): return self
    def __exit__(self,*_): self.ws.close()
    def on(self,name,handler): self.handlers[name]=handler
    def call(self,method,params=None):
        self.serial+=1
        self.ws.send(json.dumps({'id':self.serial,'method':method,'params':params or {}}))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            response=json.loads(self.ws.recv(timeout=max(.1,deadline-time.monotonic())))
            if response.get('id')==self.serial:
                if 'error' in response: raise RuntimeError(response['error'])
                return response.get('result',{})
            self.events.append(response)
            if response.get('method')=='Runtime.exceptionThrown' and 'pageerror' in self.handlers:
                self.handlers['pageerror'](response['params'])
        raise TimeoutError(method)
    def evaluate(self,expression):
        result=self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
        if 'exceptionDetails' in result: raise RuntimeError(result['exceptionDetails'])
        return result['result'].get('value')
    def wait_for_function(self,expression,timeout=15000):
        deadline=time.monotonic()+timeout/1000
        expression='(() => {try {return Boolean('+expression+');}catch {return false;}})()'
        while time.monotonic()<deadline:
            if self.evaluate(expression): return
            time.sleep(.05)
        raise TimeoutError(expression)
    def goto(self,url,timeout=15000):
        first=len(self.events)
        result=self.call('Page.navigate',{'url':url})
        if result.get('errorText'): raise RuntimeError(result['errorText'])
        deadline=time.monotonic()+timeout/1000
        while time.monotonic()<deadline:
            navigation_requests={event['params']['requestId'] for event in self.events[first:]
                if event.get('method')=='Network.requestWillBeSent'
                and event['params'].get('type')=='Document'
                and event['params'].get('frameId')==result.get('frameId')
                and event['params'].get('loaderId')==result.get('loaderId')}
            for event in self.events[first:]:
                # Navigation cancels the old page's polling requests. Only a
                # failure of this navigation's document should fail goto.
                if event.get('method')=='Network.loadingFailed' and event['params']['requestId'] in navigation_requests:
                    raise RuntimeError(event['params']['errorText'])
            if self.evaluate('location.href==='+json.dumps(url)+' && document.readyState==="complete"'): return
            time.sleep(.05)
        raise TimeoutError(url)
    def locator(self,selector): return Locator(self,selector)

class Locator:
    def __init__(self,page,selector): self.page,self.selector=page,selector
    @property
    def element(self): return 'document.querySelector('+json.dumps(self.selector)+')'
    def count(self): return self.page.evaluate('document.querySelectorAll('+json.dumps(self.selector)+').length')
    def inner_text(self): return self.page.evaluate(self.element+'.innerText')
    def click(self):
        point=self.page.evaluate('(() => {const e='+self.element+';e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect(),z=Number(getComputedStyle(document.body).zoom)||1;return {x:(r.x+r.width/2)*z,y:(r.y+r.height/2)*z};})()')
        for kind in ('mousePressed','mouseReleased'):
            self.page.call('Input.dispatchMouseEvent',{'type':kind,'x':point['x'],'y':point['y'],'button':'left','clickCount':1})
    def set_checked(self,value):
        if self.page.evaluate(self.element+'.checked')!=value: self.click()
    def select_option(self,value):
        self.page.evaluate('(() => {const e='+self.element+';e.value='+json.dumps(value)+';e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));})()')
