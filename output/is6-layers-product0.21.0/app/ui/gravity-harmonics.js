'use strict';
let j2Snapshot=null,j2Identity='',j2Options='';
function clearJ2Editor(){j2Snapshot=null;$('j2-editor-fields').disabled=true;$('j2-editor-status').textContent='Pause e carregue os parâmetros da fonte.';}
function updateGravityHarmonics(p){
  const options=p.system_id+'|'+p.bodies.map(b=>b.id).join('|');
  if(options!==j2Options){const previous=$('j2-body').value;$('j2-body').replaceChildren(...p.bodies.map(b=>new Option(b.name,b.id)));if(p.bodies.some(b=>b.id===previous))$('j2-body').value=previous;j2Options=options;}
  const body=p.bodies.find(b=>b.id===$('j2-body').value),identity=p.system_id+'|'+p.edit_token+'|'+body?.id;
  if(identity!==j2Identity){j2Identity=identity;clearJ2Editor();}
  const configuration=p.gravity_effects||{},model=body&&configuration[body.id];
  $('j2-status').textContent=Object.keys(configuration).length+'/4 fontes J2 ativas. '+(model?'Fonte selecionada: J2='+model.j2.toExponential(6)+'; Req='+model.radius_eq_m.toExponential(6)+' m.\nEixo inercial: '+model.axis.map(v=>v.toPrecision(6)).join(' / ')+'.\n'+model.provenance:'Fonte selecionada: só monopolo, J2 desativado. Nenhum planeta recebe J2 automaticamente.');
  const stale=j2Snapshot&&(p.revision!==j2Snapshot.revision||p.time!==j2Snapshot.expected_time);
  $('apply-j2').disabled=pending||!j2Snapshot||!p.paused||Boolean(stale);
  $('prepare-j2').disabled=pending||!body;
  if(stale)$('j2-editor-status').textContent='O sistema evoluiu ou mudou. Pause e carregue novamente antes de aplicar.';
}
function fillJ2Editor(){
  const p=appState?.physics,body=p?.bodies.find(b=>b.id===$('j2-body').value);if(!p?.paused||!body)return;
  const value=p.gravity_effects?.[body.id];j2Snapshot={...editGuard(p),body:body.id};
  $('j2-active').checked=Boolean(value);$('j2-coefficient').value=value?String(value.j2):'';
  $('j2-radius').value=value?String(value.radius_eq_m):'';$('j2-provenance').value=value?.provenance||'';
  (value?.axis||[0,0,1]).forEach((v,i)=>$('j2-axis-'+i).value=String(v));
  $('j2-editor-fields').disabled=false;$('j2-parameters').disabled=!value;
  $('j2-editor-status').textContent='Fonte: '+body.name+' · revisão '+p.revision+'. Eixo em '+p.contract.frame+'. Alterar J2 registra intervenção de energia e reinicia os derivados do integrador.';
  updateGravityHarmonics(p);
}
$('j2-body').onchange=()=>{clearJ2Editor();if(appState?.physics)updateGravityHarmonics(appState.physics);};
$('j2-active').onchange=()=>{$('j2-parameters').disabled=!$('j2-active').checked;};
$('prepare-j2').onclick=async()=>{await command({command:'pause'},'Experimento pausado para editar J2.');fillJ2Editor();};
$('j2-form').onsubmit=async event=>{
  event.preventDefault();if(pending||!j2Snapshot||!$('j2-form').reportValidity())return;
  const revision=j2Snapshot.revision,parameters=$('j2-active').checked?{
    j2:Number($('j2-coefficient').value),radius_eq_m:Number($('j2-radius').value),
    axis:[0,1,2].map(i=>Number($('j2-axis-'+i).value)),provenance:$('j2-provenance').value}:null;
  await command({...j2Snapshot,command:'set_j2',parameters},parameters?'J2 aplicado e pausado; energia da intervenção registrada.':'J2 desativado e pausado; energia da intervenção registrada.');
  if(appState?.physics?.revision===revision+1)fillJ2Editor();
};
