'use strict';
let cloudPanel='experience',cloudPopulationKey=null;
function showCloudPanel(name){
  cloudPanel=cloudPanel===name?null:name;
  document.documentElement.classList.toggle('panel-closed',!cloudPanel);
  document.querySelectorAll('[data-workspace-panel]').forEach(panel=>panel.hidden=panel.dataset.workspacePanel!==cloudPanel);
  renderCloudWorkspace();
}
function renderCloudWorkspace(){
  if(state){const key=state.system_id+'|'+state.edit_token;if(key!==cloudPopulationKey){cloudPopulationKey=key;const value=String(state.count);if(![...$('count').options].some(o=>o.value===value))$('count').add(new Option(value,value));$('count').value=value;}}
  document.querySelectorAll('[data-cloud-panel]').forEach(button=>{
    button.disabled=false;button.setAttribute('aria-expanded',String(button.dataset.cloudPanel===cloudPanel));
  });
  document.querySelectorAll('[data-close-panel]').forEach(button=>button.disabled=false);
  if(state)$('compact-rate').textContent='Ritmo '+num(state.requested_model_s_per_wall_s)+' s/s';
}
function applyCloudScale(value){
  const scale=[1,1.25,1.5].includes(Number(value))?Number(value):1;
  document.body.style.zoom=String(scale);document.body.style.width='calc(100vw / '+scale+')';
  document.body.style.height='calc(100vh / '+scale+')';$('interface-scale').value=String(scale);
  try{localStorage.setItem('cosmos2.em.cloudEditor.uiScale',String(scale));}catch{}
}
document.querySelectorAll('[data-cloud-panel]').forEach(button=>button.onclick=()=>showCloudPanel(button.dataset.cloudPanel));
document.querySelectorAll('[data-close-panel]').forEach(button=>button.onclick=()=>{
  const previous=cloudPanel;showCloudPanel(cloudPanel);document.querySelector('[data-cloud-panel="'+previous+'"]').focus();
});
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&cloudPanel){const previous=cloudPanel;showCloudPanel(cloudPanel);document.querySelector('[data-cloud-panel="'+previous+'"]').focus();}
});
$('interface-scale').onchange=()=>applyCloudScale($('interface-scale').value);
try{applyCloudScale(localStorage.getItem('cosmos2.em.cloudEditor.uiScale'));}catch{applyCloudScale(1);}
window.renderCloudWorkspace=renderCloudWorkspace;
renderCloudWorkspace();
