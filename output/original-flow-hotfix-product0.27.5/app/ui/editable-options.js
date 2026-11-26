/* Editable species suggestions in the document, without a native popup widget. */
(() => {
  'use strict';
  const controls=new Map(), portal=document.createElement('div'), list=document.createElement('div');
  let opened=null, serial=0;
  portal.className='c2-options-portal c2-suggestions-portal';portal.hidden=true;portal.setAttribute('popover','manual');
  list.className='c2-options-list c2-suggestions-list';list.id='c2-suggestions-list';list.setAttribute('role','listbox');
  portal.append(list);document.documentElement.append(portal);
  const disabled=c=>c.input.matches(':disabled')||c.input.readOnly;
  const plain=text=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();
  function close(){
    if(!opened)return;
    opened.control.input.setAttribute('aria-expanded','false');opened.control.input.removeAttribute('aria-activedescendant');
    opened=null;portal.hidden=true;if(portal.matches(':popover-open'))portal.hidePopover();list.replaceChildren();
  }
  function position(){
    if(!opened)return;
    const input=opened.control.input,r=input.getBoundingClientRect(),style=getComputedStyle(input),body=document.body;
    const zoom=Number(getComputedStyle(body).zoom)||1,ratio=body.getBoundingClientRect().width/parseFloat(getComputedStyle(body).width);
    const factor=Math.abs(ratio-1)<.02?zoom:1;
    list.style.fontFamily=style.fontFamily;list.style.fontSize=Math.max(14,parseFloat(style.fontSize)*zoom)+'px';
    list.style.setProperty('--choice-row-height',Math.max(38,32*zoom)+'px');
    list.style.width=Math.min(innerWidth-16,Math.max(r.width*factor,240*zoom))+'px';
    list.style.left=Math.max(8,Math.min(r.left*factor,innerWidth-list.offsetWidth-8))+'px';
    const below=innerHeight-r.bottom*factor-12,above=r.top*factor-12;
    const upwards=below<Math.min(250*zoom,list.scrollHeight)&&above>below;
    list.style.maxHeight=Math.min(360*zoom,Math.max(70,upwards?above:below))+'px';
    list.style.top=Math.max(8,Math.min(innerHeight-list.offsetHeight-8,upwards?r.top*factor-list.offsetHeight-5:r.bottom*factor+5))+'px';
  }
  function highlight(index){
    if(!opened)return;opened.index=index;
    list.querySelectorAll('[role=option]').forEach((row,i)=>{
      row.classList.toggle('c2-option-active',i===index);
      if(i===index){opened.control.input.setAttribute('aria-activedescendant',row.id);row.scrollIntoView({block:'nearest'});}
    });
  }
  function commit(index){
    if(!opened)return;
    const {control,options}=opened,option=options[index];if(!option||disabled(control))return;
    const changed=control.input.value!==option.value;
    control.input.value=option.value;close();control.committing=true;
    try{if(changed){control.input.dispatchEvent(new Event('input',{bubbles:true}));control.input.dispatchEvent(new Event('change',{bubbles:true}));}}
    finally{control.committing=false;}
  }
  function render(){
    if(!opened)return;
    const control=opened.control,input=control.input,data=document.getElementById(control.listId),query=plain(input.value.trim());
    const matches=[...(data?.options||[])].filter(o=>!o.disabled&&!o.hidden&&(plain(o.value).includes(query)||plain(o.label).includes(query)));
    opened.query=input.value;opened.options=matches.slice(0,60);list.replaceChildren();
    opened.options.forEach((option,index)=>{
      const row=document.createElement('div');row.className='c2-choice-option c2-suggestion-option';row.id='c2-suggestion-'+control.id+'-'+index;
      row.setAttribute('role','option');row.setAttribute('aria-selected',String(option.value===input.value));row.dataset.suggestionValue=option.value;
      const value=document.createElement('span'),detail=document.createElement('small');value.textContent=option.value;detail.textContent=option.label===option.value?'':option.label;row.append(value,detail);
      row.addEventListener('pointerdown',e=>e.preventDefault());row.addEventListener('pointermove',()=>highlight(index));
      row.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();commit(index);});list.append(row);
    });
    if(!matches.length||matches.length>60){
      const hint=document.createElement('div');hint.className='c2-choice-empty';hint.setAttribute('role','status');
      hint.textContent=matches.length?'Mostrando 60 de '+matches.length+' sugestões. Continue digitando para filtrar.':'Nenhuma sugestão. Confira a identificação ou continue digitando.';
      list.append(hint);
    }
    position();highlight(opened.options.findIndex(o=>o.value===input.value));
  }
  function show(control){
    if(disabled(control))return;
    document.dispatchEvent(new Event('cosmos2-close-choices'));
    if(opened?.control!==control){close();opened={control,index:-1,options:[],query:null};portal.hidden=false;portal.showPopover();control.input.setAttribute('aria-expanded','true');}
    render();
  }
  function enhance(input){
    if(controls.has(input))return;
    const listId=input.getAttribute('list');if(!listId)return;
    input.dataset.c2List=listId;input.removeAttribute('list');
    input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');input.setAttribute('aria-controls',list.id);
    const control={input,listId,id:++serial,committing:false};controls.set(input,control);
    input.addEventListener('focus',()=>show(control));input.addEventListener('click',()=>{if(!opened)show(control);});
    input.addEventListener('input',()=>{if(!control.committing)show(control);});
    input.addEventListener('blur',()=>setTimeout(()=>{if(opened?.control===control&&document.activeElement!==input)close();},0));
    input.addEventListener('keydown',event=>{
      if(disabled(control))return;
      if(event.key==='Escape'&&opened?.control===control){event.preventDefault();event.stopPropagation();close();return;}
      if(event.key==='Tab'){close();return;}
      if(event.key==='ArrowDown'||event.key==='ArrowUp'){
        event.preventDefault();event.stopPropagation();if(!opened)show(control);
        if(opened.options.length)highlight(Math.max(0,Math.min(opened.options.length-1,opened.index+(event.key==='ArrowUp'?-1:1))));return;
      }
      if(event.key==='Enter'&&opened?.control===control){
        if(opened.index>=0){event.preventDefault();event.stopPropagation();commit(opened.index);}else close();
      }
    });
  }
  const discover=()=>document.querySelectorAll('input[list]').forEach(enhance);
  discover();
  document.addEventListener('pointerdown',event=>{if(opened&&!list.contains(event.target)&&event.target!==opened.control.input)close();},true);
  document.addEventListener('cosmos2-close-suggestions',close);
  let queued=false;
  const observer=new MutationObserver(()=>{if(!queued){queued=true;requestAnimationFrame(()=>{queued=false;discover();if(opened){if(disabled(opened.control)||!opened.control.input.isConnected)close();}});}});
  observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['list','disabled','readonly','hidden']});
  const timer=setInterval(()=>{
    for(const [input] of controls)if(!input.isConnected)controls.delete(input);
    if(opened){const input=opened.control.input;if(!input.isConnected||disabled(opened.control)||document.activeElement!==input)close();else if(input.value!==opened.query)render();else position();}
  },180);
  document.addEventListener('scroll',position,true);window.addEventListener('resize',position);
  window.addEventListener('pagehide',()=>{clearInterval(timer);observer.disconnect();close();},{once:true});
})();
