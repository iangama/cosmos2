'use strict';
let workspacePanel='experience';
const panelButtons=[...document.querySelectorAll('[data-panel]')];
function showPanel(name){
  workspacePanel=workspacePanel===name?null:name;
  document.documentElement.classList.toggle('panel-closed',!workspacePanel);
  document.querySelectorAll('[data-workspace-panel]').forEach(panel=>panel.hidden=panel.dataset.workspacePanel!==workspacePanel);
  renderWorkspace();
}
function renderWorkspace(){
  panelButtons.forEach(button=>{
    button.disabled=false;
    button.setAttribute('aria-expanded',String(button.dataset.panel===workspacePanel));
  });
  if(state)$('compact-rate').textContent='Ritmo '+number(state.requested_model_s_per_wall_s)+' s/s';
  document.querySelectorAll('[data-close-panel]').forEach(button=>button.disabled=false);
  if(state)$('title').textContent=state.experiment.mode==='mutual_electrostatic'?'Cargas com reação elétrica':'Partícula em campos prescritos';
}
panelButtons.forEach(button=>button.onclick=()=>showPanel(button.dataset.panel));
document.querySelectorAll('[data-close-panel]').forEach(button=>button.onclick=()=>{
  const previous=workspacePanel;showPanel(workspacePanel);
  panelButtons.find(b=>b.dataset.panel===previous)?.focus();
});
$('potential-jump').onclick=()=>{
  if(workspacePanel!=='layers')showPanel('layers');
  $('potential-panel').scrollIntoView({block:'start'});$('measure-potential').focus();
};
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&workspacePanel){
    const previous=workspacePanel;showPanel(workspacePanel);
    panelButtons.find(b=>b.dataset.panel===previous)?.focus();
  }
});
window.renderWorkspace=renderWorkspace;
function applyWorkspaceScale(value){
  const scale=[1,1.25,1.5].includes(Number(value))?Number(value):1;
  document.body.style.zoom=String(scale);
  document.body.style.width='calc(100vw / '+scale+')';
  document.body.style.height='calc(100vh / '+scale+')';
  $('interface-scale').value=String(scale);
  try{localStorage.setItem('cosmos2.em.integration.uiScale',String(scale));}catch{}
}
$('interface-scale').onchange=()=>applyWorkspaceScale($('interface-scale').value);
try{applyWorkspaceScale(localStorage.getItem('cosmos2.em.integration.uiScale'));}catch{applyWorkspaceScale(1);}
renderWorkspace();

window.commandDescription=name=>({
  pause:'Experimento pausado.',resume:'Experimento em evolução.',advance:'Passo concluído.',
  load_preset:'Experiência carregada pausada.',load:'Fase retomada pausada.',
  save:'Fase, vista e preferências de tempo salvas.',edit:'Alteração física confirmada.',
  set_controls:'Atuação física confirmada.',set_visual:'Camada ou seleção atualizada.',
  set_rate:'Ritmo solicitado atualizado.',set_timestep:'Passo de integração atualizado.',
  field_map:'Campos medidos no instante confirmado.',trace_fields:'Linhas de referência calculadas.',
  measure_particle:'Força e energia medidas no instante confirmado.'
}[name]||'Condição confirmada.');
