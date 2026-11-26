'use strict';
let timelikeJob=null;
function updateTimelikeParameters(){
  if(config.scenario!=='timelike-orbits')return;
  const circular=byId('parameters').elements.orbit_kind.value==='circular';
  document.querySelector('[data-parameter="eccentricity"]').hidden=circular;
  const input=byId('parameters').elements.eccentricity;input.disabled=circular;if(circular&&(!Number.isFinite(Number(input.value))||Number(input.value)<.05||Number(input.value)>.8))input.value=.6;
  document.querySelector('[data-parameter="radial_cycles"]').firstChild.textContent=circular?'Voltas azimutais de referência':'Ciclos radiais de referência';
}
async function timelikeRequest(path,value){
  const response=await fetch('/api/timelike/'+path,value===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
  const result=await response.json();
  if(!response.ok||result.ok===false)throw Error(result.error||'Cálculo recusado.');
  return result;
}
async function calculateTimelike(configuration){
  let state=await timelikeRequest('state');
  if(!state.busy)state=await timelikeRequest('command',{command:'compute',edit_token:state.edit_token,revision:state.revision,configuration});
  else{config=structuredClone(state.configuration);buildControls();buildParameters();lock(true);}
  timelikeJob={job_id:state.job_id,edit_token:state.edit_token,revision:state.revision};
  const identity=state.job_id;
  byId('timelike-controls').hidden=false;
  byId('cancel-timelike').disabled=false;
  try{
    while(state.busy){await new Promise(resolve=>setTimeout(resolve,80));state=await timelikeRequest('state');if(state.job_id!==identity)throw Error('O cálculo foi substituído; consulte a configuração atual.');}
    if(state.phase==='cancelled'){const error=Error('Cálculo cancelado. O último resultado completo foi preservado.');error.cancelled=true;throw error;}
    if(state.phase!=='complete'||state.published_job_id!==identity||!state.result)throw Error(state.error||'O cálculo não publicou um resultado completo.');
    return state.result;
  }finally{timelikeJob=null;byId('cancel-timelike').disabled=true;}
}
async function cancelTimelike(){
  if(!timelikeJob)return;
  byId('cancel-timelike').disabled=true;
  try{await timelikeRequest('command',{command:'cancel',...timelikeJob});status('Cancelando o cálculo; o último resultado completo permanece disponível.');}
  catch(error){status(error.message,true);}
}
function drawTimelike(r,index,w,h){
  const data=r.timelike,reading=data.readings[index],control=response.configuration.controls.gravity;
  const clocks=byId('timelike-view').value==='clocks';
  byId('axis-control').hidden=true;byId('curve-legend').hidden=true;byId('framing-control').hidden=clocks;
  byId('reference-entry').hidden=!control.visible;
  byId('time-label').textContent=`t = ${format(r.time_s[index])} s · ${data.clock_kind==='worldline_proper_time'?'τ':'relógio aplicado'} = ${format(reading.applied_clock_time_s)} s`;
  byId('viewport').dataset.mode='spatial';
  const actual=r.positions[index],other=r.reference_positions[index];
  const separation=Math.hypot(...actual.map((v,k)=>(v-other[k])*r.position_unit_m));
  byId('timelike-readings').textContent=`Raio areal: ${format(reading.radius_m)} m  ·  Velocidade coordenada: ${format(Math.hypot(...reading.velocity_coordinate_m_s))} m/s\nAtraso aplicado t − relógio: ${format(reading.applied_lag_s)} s  ·  Déficit de ritmo: ${format((1-reading.applied_clock_rate)*1e6)} ppm\nSeparação coordenada atual − Newton no mesmo t: ${format(separation)} m`;
  projectedArrows=[];
  if(clocks){
    const left=78,right=w-26,top=55,bottom=h-65;
    const current=data.readings.map(row=>row.applied_lag_s),baseline=data.readings.map(row=>row.gr_reference_lag_s);
    const ceiling=Math.max(1e-12,...current,...(control.visible?baseline:[]))*1.1;
    context.font='11px Segoe UI';
    for(let part=0;part<=4;part++){
      const y=bottom-(bottom-top)*part/4;
      context.strokeStyle='#29404b';context.beginPath();context.moveTo(left,y);context.lineTo(right,y);context.stroke();
      context.fillStyle='#acbec8';context.textAlign='right';context.fillText(format(ceiling*part/4),left-10,y+4);
      context.textAlign=part===0?'left':part===4?'right':'center';context.fillText(format(r.time_s.at(-1)*part/4),left+(right-left)*part/4,bottom+24);
    }
    context.textAlign='left';context.fillStyle='#c6dbe1';context.font='13px Segoe UI';context.fillText('Atraso em relação ao tempo coordenado · s',left,28);
    context.font='11px Segoe UI';context.fillText('Tempo coordenado t / s',(left+right)/2-60,bottom+46);
    function curve(values,color,dashed,limit){context.strokeStyle=color;context.lineWidth=2.2;context.setLineDash(dashed?[6,5]:[]);context.beginPath();values.slice(0,limit+1).forEach((value,i)=>{const x=left+(right-left)*r.time_s[i]/r.time_s.at(-1),y=bottom-(bottom-top)*value/ceiling;i?context.lineTo(x,y):context.moveTo(x,y);});context.stroke();context.setLineDash([]);}
    if(control.visible)curve(baseline,'#b2a1fa',true,baseline.length-1);
    curve(current,'#74ddd1',false,index);
    const marker=left+(right-left)*r.time_s[index]/r.time_s.at(-1);context.strokeStyle='#cce8e755';context.beginPath();context.moveTo(marker,top);context.lineTo(marker,bottom);context.stroke();
    byId('scale-label').textContent='Verde: relógio aplicado · violeta: geodésica GR de referência';
    byId('view-help').textContent='O atraso é integrado diretamente; não é obtido subtraindo relógios quase iguais.';
    return;
  }
  const focus=byId('framing').value==='focus';
  const full=r.positions.concat(r.reference_positions);
  const mins=[0,1,2].map(k=>Math.min(-2,...full.map(v=>v[k]))),maxs=[0,1,2].map(k=>Math.max(2,...full.map(v=>v[k])));
  const center=focus?[0,0,0]:mins.map((value,k)=>(value+maxs[k])/2);
  const range=focus?2*Math.max(1.5,...r.reference_positions.map(v=>Math.hypot(...v))):Math.max(...maxs.map((value,k)=>value-mins[k]));
  const scale=zoom*Math.min(w,h)*.76/range;
  function point(v){const [x,y,z]=v.map((value,k)=>value-center[k]);const a=Math.cos(azimuth)*x-Math.sin(azimuth)*y,b=Math.sin(azimuth)*x+Math.cos(azimuth)*y;return [w*.5+a*scale,h*.5+(Math.sin(elevation)*b-Math.cos(elevation)*z)*scale];}
  function path(values,color,width,dashed){context.strokeStyle=color;context.lineWidth=width;context.setLineDash(dashed?[6,5]:[]);context.beginPath();values.forEach((value,i)=>{const p=point(value);i?context.lineTo(p[0],p[1]):context.moveTo(p[0],p[1]);});context.stroke();context.setLineDash([]);}
  path([[-3,0,0],[3,0,0]],'#36515c',.7,false);path([[0,-3,0],[0,3,0]],'#36515c',.7,false);
  if(control.visible){
    path(r.reference_positions,'#b2a1fa',1.6,true);
    for(const probe of r.metric_probes){const p=point(probe.position);context.fillStyle='#81b8c577';context.beginPath();context.arc(p[0],p[1],2.5,0,Math.PI*2);context.fill();projectedArrows.push({x:p[0],y:p[1],metric:probe});}
  }
  path(r.positions.slice(0,index+1),'#74ddd1',2.3,false);
  if(data.orbit_effect_applied)for(const event of data.apsides){if(event.coordinate_time_scaled*r.time_s.at(-1)/(data.apsides.at(-1)?.coordinate_time_scaled||1)>r.time_s[index]+1e-9)continue;const p=point([event.radius_scaled*Math.cos(event.phi_rad),event.radius_scaled*Math.sin(event.phi_rad),0]);context.fillStyle='#ffce8b';context.beginPath();context.arc(p[0],p[1],3,0,Math.PI*2);context.fill();}
  const origin=point([0,0,0]);context.fillStyle='#ffe1a2';context.beginPath();context.arc(origin[0],origin[1],6,0,Math.PI*2);context.fill();
  const p=point(actual);context.fillStyle='#e4fffa';context.beginPath();context.arc(p[0],p[1],4,0,Math.PI*2);context.fill();
  context.font='12px Segoe UI';context.fillStyle='#d4dfe7';context.fillText(data.orbit_effect_applied?'Verde: geodésica atual · violeta: Newton':'Verde: reta coordenada hipotética · violeta: Newton',18,27);
  context.font='11px Segoe UI';context.fillStyle='#adbec8';context.fillText('Fonte esférica idealizada · símbolo central ampliado · pontos dourados: periastros',18,46);
  byId('scale-label').textContent=`1 unidade = ${format(r.position_unit_m)} m · coordenadas de raio areal`;
  byId('view-help').textContent=p[0]<0||p[0]>w||p[1]<0||p[1]>h?'Partícula fora da região orbital · escolha Trajetória completa':'Arraste para orbitar · use a linha do tempo · clique nas sondas de relógio/curvatura';
}
