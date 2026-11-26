/* Read-only radial reference browser. All scientific values come from pinned data. */
(()=>{
  const el=id=>document.getElementById('stellar-reference-'+id);
  const panel=el('panel'),model=el('model'),slider=el('index'),number=el('number');
  const state={catalog:null,series:null,sample:null,index:3,modelTicket:0,sampleTicket:0,timer:null,requestedSamples:0,completedSamples:0,appliedSamples:0,sampleErrors:0};
  window.stellarReferenceState=state;
  const format=value=>Number(value).toLocaleString('pt-BR',{maximumSignificantDigits:7,notation:value!==0&&(Math.abs(value)<1e-4||Math.abs(value)>=1e7)?'scientific':'standard'});
  const status=text=>el('status').textContent=text;
  async function get(operation,parameters={}){
    if(operation==='sample')state.requestedSamples++;
    try{
      const response=await fetch('/api/stellar-reference/'+operation+'?'+new URLSearchParams(parameters));
      const data=await response.json();if(!response.ok)throw Error(data.error||'Não foi possível consultar o perfil.');
      if(operation==='sample')state.completedSamples++;return data;
    }catch(error){if(operation==='sample')state.sampleErrors++;throw error;}
  }
  const plots=[['temperature','temperature_K',1e-6,false,'#8dd6dc'],['density','density_kg_m3',1,true,'#ffc477'],['pressure','pressure_Pa',1,true,'#d3a4ee']];
  function draw(){
    for(const[id,field,factor,log,color]of plots){
      const canvas=el(id),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
      ctx.clearRect(0,0,w,h);if(!state.series)continue;
      const values=state.series[field].map(v=>log?Math.log10(v*factor):v*factor);
      const lo=log?Math.floor(Math.min(...values)):0,hi=Math.ceil(Math.max(...values));
      const left=68,right=w-24,top=20,bottom=h-38;
      const x=r=>left+r*(right-left),y=v=>bottom-(v-lo)/(hi-lo)*(bottom-top);
      ctx.font='15px sans-serif';ctx.lineWidth=1;
      for(let i=0;i<=4;i++){
        const v=lo+(hi-lo)*i/4;ctx.strokeStyle='#29414f';ctx.beginPath();ctx.moveTo(left,y(v));ctx.lineTo(right,y(v));ctx.stroke();
        ctx.fillStyle='#a7bac8';ctx.textAlign='right';ctx.fillText(format(v),left-8,y(v)+5);
      }
      for(const r of[0,.25,.5,.75,1]){ctx.textAlign='center';ctx.fillText(format(r),x(r),h-15);}
      ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();
      values.forEach((v,i)=>i?ctx.lineTo(x(state.series.r_over_Rsun[i]),y(v)):ctx.moveTo(x(state.series.r_over_Rsun[i]),y(v)));ctx.stroke();
      const selected=state.index;ctx.strokeStyle='#cbdde2';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x(state.series.r_over_Rsun[selected]),top);ctx.lineTo(x(state.series.r_over_Rsun[selected]),bottom);ctx.stroke();
      ctx.fillStyle=color;ctx.beginPath();ctx.arc(x(state.series.r_over_Rsun[selected]),y(values[selected]),4,0,Math.PI*2);ctx.fill();
    }
  }
  function render(){
    draw();const sample=state.sample;
    el('reading').textContent='';el('quality').textContent='';el('comparison').textContent='';el('abundances').replaceChildren();
    if(!sample)return;
    const p=sample.structure;
    el('reading').textContent=`${sample.model} · linha ${sample.index}/2000\nr/R☉: ${format(sample.r_over_Rsun)}\nTemperatura: ${format(p.temperature_K)} K\nDensidade: ${format(p.density_kg_m3)} kg/m³\nPressão: ${format(p.pressure_Pa)} Pa\nElétrons livres: ${format(p.electron_density_m3)} m⁻³\nVelocidade do som: ${format(p.sound_speed_m_s)} m/s`;
    const flags={central_interpolation_residue:'Centro: resíduos de interpolação preservados; excluído da comparação EOS.',inconsistent_log_radius:'Raio logarítmico inconsistente perto do centro; excluído da comparação EOS.',signed_auxiliary_source_values:'Auxiliares assinados preservados; não usados como produção local.'};
    el('quality').textContent=sample.quality_flags.map(flag=>flags[flag]||flag).join(' ');
    const c=sample.ideal_comparison;
    el('comparison').textContent=c?`P ideal: ${format(c.ideal_pressure_lower_Pa)} a ${format(c.ideal_pressure_upper_Pa)} Pa\n100 × (P ideal/P referência − 1): ${format(100*c.pressure_relative_lower)}% a ${format(100*c.pressure_relative_upper)}%\nMassa não coberta: ${format(c.uncovered_mass_fraction)}`:
      (['GS98','AGSS09'].includes(sample.model)?'Sem comparação nesta linha: fora do domínio elegível ou amostra central excluída.':'Comparação ideal disponível somente para GS98 e AGSS09.');
    for(const[name,value]of Object.entries(sample.abundances)){
      const row=document.createElement('tr');for(const text of[name,format(value)]){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}el('abundances').append(row);
    }
    status(`Amostra tabulada ${sample.index}/2000 · sem interpolação da sonda`);
  }
  function busy(value){for(const input of[model,slider,number,el('reload')])input.disabled=value;}
  async function loadModel(){
    const ticket=++state.modelTicket;++state.sampleTicket;clearTimeout(state.timer);busy(true);
    state.series=state.sample=null;render();status('Carregando perfil e amostra…');
    try{
      const[series,sample]=await Promise.all([get('series',{model:model.value}),get('sample',{model:model.value,index:state.index})]);
      if(ticket!==state.modelTicket)return;state.series=series;state.sample=sample;state.appliedSamples++;render();
    }catch(error){if(ticket===state.modelTicket)status(error.message);}
    finally{if(ticket===state.modelTicket)busy(false);}
  }
  function selectIndex(index){
    if(!Number.isInteger(index)||index<0||index>2000){number.value=state.index;status('Escolha um índice inteiro de 0 a 2000.');return;}
    state.index=index;slider.value=number.value=String(index);draw();status(`Consultando amostra ${index}; a sonda mantém a última linha confirmada.`);
    const ticket=++state.sampleTicket,modelTicket=state.modelTicket;clearTimeout(state.timer);
    state.timer=setTimeout(async()=>{
      try{const sample=await get('sample',{model:model.value,index});if(ticket!==state.sampleTicket||modelTicket!==state.modelTicket)return;state.sample=sample;state.appliedSamples++;render();}
      catch(error){if(ticket===state.sampleTicket&&modelTicket===state.modelTicket)status(error.message);}
    },90);
  }
  async function open(){
    panel.hidden=false;document.getElementById('open-stellar-reference').setAttribute('aria-expanded','true');el('scale').value=document.getElementById('ui-scale').value;el('close').focus();
    if(state.catalog){draw();return;}
    busy(true);status('Carregando catálogo de referência…');
    try{
      state.catalog=await get('catalog');model.replaceChildren(...state.catalog.models.map(name=>new Option(name,name)));
      await loadModel();
    }catch(error){status(error.message);busy(false);}
  }
  function close(){panel.hidden=true;document.getElementById('open-stellar-reference').setAttribute('aria-expanded','false');document.getElementById('open-stellar-reference').focus();}
  document.getElementById('open-stellar-reference').onclick=open;el('close').onclick=close;
  el('reload').onclick=()=>state.catalog?loadModel():open();
  model.onchange=loadModel;slider.oninput=()=>selectIndex(Number(slider.value));number.onchange=()=>{if(!number.value||!number.checkValidity()){number.value=state.index;status('Escolha um índice inteiro de 0 a 2000.');return;}selectIndex(Number(number.value));};
  el('scale').onchange=()=>{const global=document.getElementById('ui-scale');global.value=el('scale').value;global.dispatchEvent(new Event('change'));};
  for(const[id]of plots)el(id).onclick=event=>{if(!state.series)return;const box=event.currentTarget.getBoundingClientRect();selectIndex(Math.max(0,Math.min(2000,Math.round(((event.clientX-box.left)*900/box.width-68)/(900-24-68)*2000))));};
  panel.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}});
})();
