"""Preserve serviceA; avoid the helper's command/name keyword collision for branches."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'scripts/verify-is6-expanded-journey-service-v2.py';assert not target.exists()
text=(ROOT/'scripts/verify-is6-expanded-journey-service.py').read_text(encoding='utf8')
anchor='def physical(p):\n'
wrapper='''class ExpandedWorker(helpers.Worker):
    def call(self,command_name,expect_error=False,**fields):
        self.serial+=1
        self.process.stdin.write(json.dumps(dict(command=command_name,id=self.serial,**fields),allow_nan=False)+'\\n')
        self.process.stdin.flush()
        import time
        deadline=time.monotonic()+40
        while True:
            response=self.events.get(timeout=max(.001,deadline-time.monotonic()))
            assert response['type'] not in ('eof','invalid'),response
            if response['type']=='snapshot':self.latest=response
            if response.get('id')==self.serial and response['type'] in ('ack','error'):
                assert (response['type']=='error')==expect_error,response
                return response


'''
assert text.count(anchor)==1;text=text.replace(anchor,wrapper+anchor)
text=text.replace('worker=helpers.Worker(storage)','worker=ExpandedWorker(storage)')
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,product_changed=False,reason='Worker helper name parameter collided with branch payload name; protocol adapter only.')))
