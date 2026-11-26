'use strict';
// Actual frozen results; a deliberately controlled HTTP worker for cancellation/error states.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),args=Object.fromEntries(process.argv.slice(2).map(s=>s.split('=')));
const label=args['--label'];assert(/^[a-z0-9-]+$/.test(label||''));
const product=path.resolve(root,args['--product']),ui=path.join(product,'app/ui');
const out=path.join(root,`evidence/working-orbits-ui-${label}.json`);assert(!fs.existsSync(out));
const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex'),digest=v=>crypto.createHash('sha256').update(JSON.stringify(v)).digest('hex');
const clone=v=>JSON.parse(JSON.stringify(v)),read=f=>JSON.parse(fs.readFileSync(path.join(root,f),'utf8'));
const catalog=read('output/working-orbits-ui-fixtures-20261121a/catalog.json');
const gravity=read('output/forces-confirmed-ui-fixtures-20261120a/gravity.json');
const profile=read('evidence/c214-orbits-profile-20261121b.json'),records={};
for(const run of profile.runs){const expected=run.stable_control.expected_scenario;records[run.recipe.name]=read(`output/c214-orbits-profile-20261121b/http-objects/${expected.body_sha256}.json`).result;}
let fixture;function reset(){fixture={slow:false,seq:0,posts:[],state:{busy:false,revision:0,edit_token:'fixture',job_id:null},saved:null};}
function reply(res,status,value,type='application/json'){res.writeHead(status,{'Content-Type':type,'Cache-Control':'no-store'});res.end(type==='application/json'?JSON.stringify(value):value);}
const server=http.createServer(async(req,res)=>{
 const route=new URL(req.url,'http://localhost').pathname;
 if(route==='/api/forces/catalog')return reply(res,200,catalog);
 if(route==='/api/timelike/state')return reply(res,200,fixture.state);
 if(route.startsWith('/api/')){
  let raw='';for await(const chunk of req)raw+=chunk;const body=raw?JSON.parse(raw):{};fixture.posts.push({route,body:clone(body)});
  if(route==='/api/forces/evaluate')return reply(res,200,gravity);
  if(route==='/api/timelike/command'){
   if(body.command==='cancel'){fixture.state={...fixture.state,busy:false,phase:'cancelled'};return reply(res,200,fixture.state);}
   if(!Number.isInteger(body.configuration.parameters.radial_cycles))return reply(res,400,{ok:false,error:'Escolha um número inteiro de ciclos.'});
   const result=body.configuration.parameters.orbit_kind==='circular'?records['circular-orbit']:records['eccentric-orbit'];
   const job_id='fixture-job-'+(++fixture.seq);
   fixture.state={busy:fixture.slow,phase:fixture.slow?'computing':'complete',job_id,published_job_id:fixture.slow?null:job_id,
     revision:fixture.seq,edit_token:'fixture-'+fixture.seq,configuration:result.configuration,result:fixture.slow?null:result};
   return reply(res,200,fixture.state);
  }
  if(route==='/api/forces/save'){fixture.saved=body;return reply(res,200,{ok:true,saved:{configuration:body}});}
  if(route==='/api/forces/export')return reply(res,200,{...records['circular-orbit'],export_file:'controlled-fixture.json'});
  return reply(res,404,{ok:false,error:'Unexpected fixture request'});
 }
 const file=path.join(ui,route.slice(1));if(/^\/[a-z0-9.-]+\.(html|css|js)$/.test(route)&&fs.existsSync(file))return reply(res,200,fs.readFileSync(file),route.endsWith('js')?'text/javascript':route.endsWith('css')?'text/css':'text/html');
 reply(res,404,{});
});
const proof={accepted:false,completed:false,native_user_flow_accepted:false,checks:[],product:path.relative(root,product),
 source_sha256:Object.fromEntries(['forces.js','forces.html','forces.css','timelike-view.js','option-controls.js'].map(n=>[path.relative(root,path.join(ui,n)),sha(path.join(ui,n))])),
 scope:'Isolated browser UI with real frozen physics outputs and an explicit controlled HTTP worker. Tests complete/circular/error/confirmed save+export and first-job cancellation. No live owner session, native acceptance, new science or performance measurement.'};
let browser;
async function main(){
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const {chromium}=require('/home/an/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');browser=await chromium.launch({headless:true});
 for(const [name,run] of [
  ['first-job-cancellation-restores-previous-result-controls',async p=>{
   const before=await p.evaluate(()=>JSON.stringify(response));fixture.slow=true;
   await p.locator('[data-scenario="timelike-orbits"]').click();await p.locator('#cancel-timelike').waitFor({state:'visible'});
   await p.waitForFunction(()=>!document.getElementById('cancel-timelike').disabled);await p.locator('#cancel-timelike').click();await p.waitForFunction(()=>!pending);
   assert.equal(await p.evaluate(()=>JSON.stringify(response)),before);assert.equal(await p.evaluate(()=>config.scenario),'gravity');
   assert(await p.locator('#timelike-controls').isHidden(),'Cancelled first job must restore controls of the confirmed gravity result');
  }],
  ['complete-circular-error-save-and-export-use-confirmed-result',async p=>{
   await p.locator('[data-scenario="timelike-orbits"]').click();await p.waitForFunction(()=>!pending&&response.result.timelike);
   assert.equal(await p.locator('#time-index').getAttribute('max'),'1024');
   await p.locator('#parameters [name="orbit_kind"]').selectOption('circular');assert(await p.locator('[data-parameter="eccentricity"]').isHidden());
   await p.locator('#calculate').click();await p.waitForFunction(()=>!pending&&config.parameters.orbit_kind==='circular');
   const before=await p.evaluate(()=>JSON.stringify(response));
   await p.locator('#parameters [name="radial_cycles"]').fill('1.5');await p.locator('#calculate').click();await p.waitForFunction(()=>!pending&&document.getElementById('force-status').classList.contains('error'));
   assert.equal(await p.evaluate(()=>JSON.stringify(response)),before);assert(await p.locator('#result-draft-note').isVisible());
   await p.locator('#save-forces').click();await p.waitForFunction(()=>!pending);assert.equal(fixture.saved.parameters.radial_cycles,8);
   await p.locator('#export-forces').click();await p.waitForFunction(()=>!pending);assert.equal(await p.evaluate(()=>lastForcesExport.physics_sha256),records['circular-orbit'].physics_sha256);
  }]
 ]){
  reset();const p=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
  try{await p.goto(`http://127.0.0.1:${server.address().port}/forces.html`);await p.waitForFunction(()=>typeof response!=='undefined'&&response&&!pending);await run(p);assert.deepEqual(errors,[]);proof.checks.push({name,passed:true});}
  catch(e){proof.checks.push({name,passed:false,error:e.message,page_errors:errors});}
  finally{await p.close();}
 }
 proof.completed=true;proof.accepted=proof.checks.every(c=>c.passed);
}
main().catch(e=>proof.failure=e.stack).finally(async()=>{if(browser)await browser.close();await new Promise(r=>server.close(r));proof.script_sha256=sha(__filename);fs.writeFileSync(out,JSON.stringify(proof,null,2)+'\n');console.log(JSON.stringify(proof));process.exitCode=proof.accepted?0:1;});
