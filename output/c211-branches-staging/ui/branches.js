'use strict';
let branchOptions='',branchComparison=null,branchSystem=null;
function updateBranches(p){
  const catalog=p.branches;if(!catalog)return;
  if(branchSystem!==p.system_id){branchSystem=p.system_id;branchComparison=null;$('branch-comparison-status').textContent='';drawBranchChart();}
  const options=JSON.stringify(catalog.branches.map(r=>[r.id,r.name,r.system_id]));
  if(options!==branchOptions){
    for(const id of ['branch-first','branch-second']){
      const previous=$(id).value;$(id).replaceChildren(...catalog.branches.map(r=>new Option(r.name+' · '+r.id.slice(-6),r.id)));
      if(catalog.branches.some(r=>r.id===previous))$(id).value=previous;
    }
    if(catalog.branches.length>1&&$('branch-first').value===$('branch-second').value)$('branch-second').selectedIndex=1;
    branchOptions=options;
  }
  const active=catalog.branches.find(r=>r.id===catalog.active_id);
  $('branch-status').textContent=catalog.error||catalog.branches.length+'/'+catalog.maximum_branches+' arquivos · '+(active?'Origem da evolução atual: '+active.name+' · '+active.id.slice(-6)+'.':'Nenhum arquivo selecionado como pai da evolução atual.');
  $('branch-create').disabled=pending||Boolean(catalog.error)||catalog.branches.length>=catalog.maximum_branches;
  $('branch-load').disabled=pending||!catalog.branches.length;
  const a=catalog.branches.find(r=>r.id===$('branch-first').value),b=catalog.branches.find(r=>r.id===$('branch-second').value);
  $('branch-compare').disabled=pending||!a||!b||a.id===b.id;
  $('branch-export').disabled=pending||!branchComparison;
}
async function branchRequest(commandName,extra={}){
  await command({command:'pause'},'Evolução pausada para trabalhar com os arquivos.');
  const p=appState.physics;if(!p?.paused)return;
  return command({...editGuard(p),command:commandName,...extra},'Arquivo confirmado.');
}
$('branch-create').onclick=async()=>{
  const name=$('branch-name').value,result=await branchRequest('create_branch',{name});
  const id=result?.ack?.result?.id;if(id)$('branch-first').value=id;
};
$('branch-load').onclick=()=>branchRequest('load_branch',{branch_id:$('branch-first').value});
$('branch-compare').onclick=async()=>{
  const result=await branchRequest('compare_branches',{first_id:$('branch-first').value,second_id:$('branch-second').value});
  const compared=result?.ack?.result;if(!compared)return;
  branchComparison=compared;
  const all=[...new Map([...compared.first_curves.samples,...compared.second_curves.samples].flatMap(r=>r.probes).map(p=>[p.id,p])).values()];
  $('branch-probe').replaceChildren(...all.map(p=>new Option(p.name+' · '+p.id.slice(-6),p.id)));
  const missing=compared.body_differences.filter(r=>!r.available_in_first||!r.available_in_second).length;
  $('branch-comparison-status').textContent=compared.frame+'\nInstantes finais: '+historyNumber(compared.first.time*appState.physics.physical_scale.time_unit_s)+' / '+historyNumber(compared.second.time*appState.physics.physical_scale.time_unit_s)+' s.\n'+(compared.same_physical_instant?'Diferenças dos estados finais calculadas no mesmo instante físico.':'Instantes finais diferentes; estados finais não são subtraídos.')+'\n'+missing+' identidades ausentes de um dos ramos; leituras indisponíveis ficam como lacunas.'+(compared.definition_variation_probe_ids.length?'\nAtenção: definições de sonda variam entre as janelas. Consulte posições e exclusões originais no histórico de cada ramo.':'');
  drawBranchChart();updateBranches(appState.physics);
};
$('branch-export').onclick=async()=>{
  if(!branchComparison)return;
  const result=await branchRequest('export_branches',{first_id:branchComparison.first.id,second_id:branchComparison.second.id});
  if(result?.ack?.export_file)$('notice').textContent='Exportado: '+result.ack.export_file;
};
function drawBranchChart(){
  const canvas=$('branch-chart'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#0b1925';ctx.fillRect(0,0,w,h);ctx.font='20px sans-serif';ctx.fillStyle='#b4d5df';
  if(!branchComparison){ctx.fillText('Selecione e compare dois arquivos',15,165);$('branch-chart-legend').textContent='';return;}
  const quantity=$('branch-quantity').value,probe=$('branch-probe').value,integral=['energy_J','energy_error'].includes(quantity);
  const sources=[branchComparison.first_curves.samples,branchComparison.second_curves.samples];
  const series=sources.map(rows=>rows.map(row=>({row,value:integral?row.integrals[quantity]:row.probes.find(p=>p.id===probe&&p.available)?.[quantity]})));
  const valid=series.flat().filter(p=>Number.isFinite(p.value));
  if(!valid.length){ctx.fillText('Sem leituras disponíveis',15,165);$('branch-chart-legend').textContent='Grave sondas durante a evolução e arquive a janela em cada ramo.';return;}
  let ymin=Math.min(...valid.map(p=>p.value)),ymax=Math.max(...valid.map(p=>p.value));
  if(ymin===ymax){const margin=Math.max(Math.abs(ymin)*.03,1e-30);ymin-=margin;ymax+=margin;}
  const offset=(ymax-ymin)<.01*Math.max(Math.abs(ymin),Math.abs(ymax))?(ymin+ymax)/2:0;
  const times=sources.flat().map(r=>r.time_s),xmin=Math.min(...times),xmax=Math.max(...times),left=112,right=w-16,top=35,bottom=h-60;
  const x=t=>left+(t-xmin)/(xmax===xmin?1:xmax-xmin)*(right-left),y=v=>bottom-(v-ymin)/(ymax-ymin)*(bottom-top);
  ctx.strokeStyle='#355264';ctx.lineWidth=1;
  for(let i=0;i<3;i++){const v=ymin+(ymax-ymin)*i/2,yy=y(v);ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();ctx.fillText((v-offset).toExponential(2),5,yy+6);}
  ctx.fillText(xmin.toExponential(2),left,bottom+32);ctx.textAlign='right';ctx.fillText(xmax.toExponential(2),right,bottom+32);ctx.textAlign='left';ctx.fillText('t (s)',(left+right)/2-18,h-7);
  series.forEach((points,k)=>{
    ctx.fillStyle=ctx.strokeStyle=k?'#ffb35a':'#79dbeb';ctx.lineWidth=3;let previous=null;
    for(const point of points){
      if(!Number.isFinite(point.value)){previous=null;continue;}
      const current={x:x(point.row.time_s),y:y(point.value)};
      if(previous&&!point.row.break_before.length){ctx.beginPath();ctx.moveTo(previous.x,previous.y);ctx.lineTo(current.x,current.y);ctx.stroke();}
      ctx.beginPath();ctx.arc(current.x,current.y,3.5,0,Math.PI*2);ctx.fill();previous=current;
    }
  });
  $('branch-chart-legend').textContent=historyQuantities[quantity]+'\nCiano: '+branchComparison.first.name+' · '+branchComparison.first.id.slice(-6)+'\nLaranja: '+branchComparison.second.name+' · '+branchComparison.second.id.slice(-6)+(offset?'\nEixo vertical: diferença em relação a '+offset.toExponential(10)+' na unidade acima.':'')+'\nInstantes originais da mesma origem física. Sem interpolar ou alinhar índices; traços interrompem lacunas.';
}
for(const id of ['branch-probe','branch-quantity'])$(id).addEventListener('change',drawBranchChart);
