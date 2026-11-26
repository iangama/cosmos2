"""Open and choose page-rendered options using genuine Windows mouse input."""
import json
from ordinary_native_input_v8 import NativeInput


class OptionInput(NativeInput):
    def open_options(self, source):
        expression='document.querySelector('+json.dumps(source)+')'
        self.page.wait_for_function(expression+'&&!'+expression+'.matches(":disabled")',timeout=20000)
        trigger='#'+self.page.evaluate(expression+'.parentElement.querySelector(".c2-choice-trigger").id')
        if not self.page.evaluate('document.querySelector('+json.dumps(trigger)+').getAttribute("aria-expanded")==="true"'):
            self.key(27)
            self.click(trigger)
            self.page.wait_for_function('!document.querySelector(".c2-options-portal").hidden',timeout=4000)

    def select(self, source, value):
        self.open_options(source)
        option='[role=option][data-choice-value='+json.dumps(value)+'][aria-disabled="false"]'
        self.page.wait_for_function('document.querySelector('+json.dumps(option)+')',timeout=2000)
        self.click(option)
        self.page.wait_for_function('document.querySelector('+json.dumps(source)+').value==='+json.dumps(value)+'&&document.querySelector(".c2-options-portal").hidden',timeout=4000)
