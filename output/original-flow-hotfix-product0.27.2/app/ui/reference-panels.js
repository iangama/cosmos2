'use strict';
// Interface guidance only. Source admission and scientific models remain on the server.
window.referencePanels=(()=>{
  const locks=new Map(),previous=new Map();
  function navigationLock(owner,locked){
    locks.set(owner,locked);
    for(const button of document.querySelectorAll('header nav button,#home')){
      const blocked=[...locks].some(([kind,active])=>active&&button.id!=='open-'+kind&&button.id!=='open-stellar-reference');
      if(blocked){if(!previous.has(button))previous.set(button,button.disabled);button.disabled=true;}
      else if(previous.has(button)){button.disabled=previous.get(button);previous.delete(button);}
    }
  }
  function open(kind){
    for(const name of ['spatial','layers']){
      document.getElementById(name+'-panel').hidden=name!==kind;
      document.getElementById('open-'+name).setAttribute('aria-expanded',String(name===kind));
    }
    document.getElementById(kind+'-panel-close').focus();
  }
  function sourceStatus(otherActive){
    const p=appState?.physics;
    if(otherActive)return {ready:false,message:'Feche a outra referência pelo botão de restaurar cena antes de preparar esta vista.'};
    if(pending||atlasPending)return {ready:false,message:'Aguarde a alteração da cena em andamento.'};
    if(!appState)return {ready:false,message:'Aguarde a conexão com o simulador.'};
    if(appState.mode==='atlas')return {ready:false,action:'copy',message:'Crie uma cópia pausada de Sol, Terra, Lua e Júpiter para usar esta referência.'};
    if(!p||p.bodies.length!==4)return {ready:false,action:'atlas',message:'Esta referência usa uma cópia solar de quatro corpos. Abra Explorar e crie essa cópia. Abrir Explorar pausa e conserva o experimento atual.'};
    if(!p.paused)return {ready:false,action:'pause',message:'Pause a cópia de quatro corpos para consultar referências congeladas na mesma fase.'};
    if(['body_field_preview','fields_preview','orbit_preview','instruments_preview','probe_preview'].some(key=>appState[key]))return {ready:false,message:'Feche as prévias de campo e as sondas no painel do experimento antes de abrir esta referência.'};
    return {ready:true,message:'Escolha o corpo e abra a referência. A cópia orbital permanece pausada.'};
  }
  function renderStart(kind,source,busy,hidden){
    const el=id=>document.getElementById(kind+'-'+id);
    el('start').hidden=hidden;
    el('source-help').textContent=source.message;
    for(const action of ['copy','atlas','pause']){
      el(action).hidden=source.action!==action;
      el(action).disabled=busy||pending||(action==='copy'&&(!atlasState||atlasPending));
    }
  }
  async function readJSON(path,options,timeout=15000){
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
    try{
      const response=await fetch(path,{...options,signal:controller.signal});
      let value;
      try{value=await response.json();}catch{throw Error('O servidor enviou uma resposta inválida. Tente novamente.');}
      if(!response.ok||value?.ok===false)throw Error(value?.error||'O servidor não confirmou a operação.');
      return value;
    }catch(error){
      if(error.name==='AbortError')throw Error('O servidor demorou para responder. Tente novamente.');
      if(error instanceof TypeError)throw Error('Não foi possível conectar ao servidor local. Tente novamente.');
      throw error;
    }finally{clearTimeout(timer);}
  }
  return {navigationLock,open,sourceStatus,renderStart,readJSON};
})();
