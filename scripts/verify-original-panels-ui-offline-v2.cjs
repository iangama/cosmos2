'use strict';
// Isolated HTML/JS regression checks with frozen HTTP fixtures. No renderer or owner session.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const options=Object.fromEntries(process.argv.slice(2).map(value=>{const i=value.indexOf('=');return i<0?[value,true]:[value.slice(0,i),value.slice(i+1)];}));
const label=options['--label'];
assert(/^[a-z0-9-]+$/.test(label||''),'Supply --label=...');
const target=path.resolve(root,options['--candidate']||'output/original-flow-hotfix-staging-v2');
const ui=path.join(target,'app/ui');
const out=path.join(root,'evidence',`original-panels-ui-offline-${label}.json`);
const folder=path.join(root,'output',`original-panels-ui-offline-${label}`);
assert(!fs.existsSync(out)&&!fs.existsSync(folder),'Preserve evidence; use a new label.');
fs.mkdirSync(folder);
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const files=['index.html','is6-spatial.js','is6-layers.js','is6-spatial.css','is6-layers.css','style.css','reference-panels.js'].filter(name=>fs.existsSync(path.join(ui,name)));
const sources=Object.fromEntries([...files.map(name=>path.join(ui,name)),__filename].map(file=>[path.relative(root,file).split(path.sep).join('/'),sha(file)]));
const clone=value=>JSON.parse(JSON.stringify(value));
const bodies=[['sun','Sol','10'],['earth','Terra','399'],['moon','Lua','301'],['jupiter','Júpiter','599']].map(([id,name,code])=>({id,name,reference_id:'sol:naif:'+code}));
const phase=()=>({system_id:'offline-source',edit_token:'offline-token',revision:1,time:0,contract:{frame:'GALACTIC'},paused:true,bodies:clone(bodies),atlas_initial:{kind:'solar_four_physical_centers'}});
const snapshot=kind=>({guard:{session_id:'offline-'+kind,artifact_id:null,revision:0},active:false,busy:false,recovery_required:false,error:null,artifact:null,checkpoint_available:false,branches:[],import_preview:null});
let fixture;
function reset(){fixture={app:{mode:'experiment',physics:phase()},snapshots:{spatial:snapshot('spatial'),layers:snapshot('layers')},fail:false,invalid:false,posts:[],commandError:null};}
reset();
const proof={accepted:false,completed:false,native_user_flow_accepted:false,installed:false,
  scope:'Headless Chromium, existing panel HTML/JS and frozen HTTP source adapters only. No native model execution, renderer, original launcher, owner session, performance or integrated-product acceptance.',
  target:path.relative(root,target).split(path.sep).join('/'),source_sha256:sources,checks:[],screenshots:[],unexpected_requests:[]};
const bootstrap=()=>`let appState=${JSON.stringify(fixture.app)},pending=false,atlasPending=false,atlasState={epoch:{utc:'2026-11-14T00:00:00Z'}};
window.fixtureCommands=[];
async function command(request,message,endpoint='/api/command'){
 window.fixtureCommands.push({request,endpoint});
 if(request.command==='atlas'){appState.mode='atlas';if(appState.physics)appState.physics.paused=true;}
 if(request.command==='pause')appState.physics.paused=true;
 if(endpoint==='/api/solar/experiment'){appState.mode='experiment';appState.physics=${JSON.stringify(phase())};}
 return {ok:true};
}`;
function respond(res,status,value,type='application/json'){
 res.writeHead(status,{'Content-Type':type,'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'"});
 res.end(type==='application/json'?JSON.stringify(value):value);
}
const server=http.createServer(async(req,res)=>{
 const pathname=new URL(req.url,'http://127.0.0.1').pathname;
 const match=pathname.match(/^\/api\/(spatial|layers)\/(state|command|import-preview|import-commit)$/);
 if(match){
  const [,kind,operation]=match;
  if(operation==='state')return respond(res,fixture.fail?503:200,fixture.fail?{ok:false,error:'Servidor de referência indisponível.'}:fixture.invalid?{}:fixture.snapshots[kind]);
  let raw='';for await(const chunk of req)raw+=chunk;
  const body=JSON.parse(raw);fixture.posts.push({kind,operation,body});
  if(fixture.commandError)return respond(res,400,{ok:false,error:fixture.commandError});
  const s=fixture.snapshots[kind];s.guard.revision++;
  let result={};
  if(body.command==='leave'){s.active=false;s.recovery_required=false;}
  if(operation==='import-preview')s.import_preview={id:'fixture-preview',valid:true,body_reference_id:'sol:naif:399',epoch:{utc:'2026-11-14T00:00:00Z'},magnetic_model:'IGRF14',visible:{spatial:true,magnetic:true},changes:[]};
  if(operation==='import-commit'){result.record={id:'new-branch',name:'Novo ramo',valid:true};s.branches.push(clone(result.record));s.import_preview=null;}
  return respond(res,200,{ok:true,[kind]:s,result});
 }
 if(pathname==='/'){
  let html=fs.readFileSync(path.join(ui,'index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');
  const selected=files.includes('reference-panels.js')?['reference-panels.js','is6-spatial.js','is6-layers.js']:['is6-spatial.js','is6-layers.js'];
  html=html.replace('</body>',`<script>${bootstrap()}</script>${selected.map(name=>`<script src="${name}"></script>`).join('')}</body>`);
  return respond(res,200,html,'text/html; charset=utf-8');
 }
 if(/^\/[a-z0-9.-]+\.(js|css)$/.test(pathname)){
  const file=path.join(ui,pathname.slice(1));
  if(fs.existsSync(file))return respond(res,200,fs.readFileSync(file),pathname.endsWith('.js')?'text/javascript':'text/css');
 }
 respond(res,404,{});
});
let browser,context;
async function test(name,run,setup){
 reset();if(setup)setup();
 const page=await context.newPage();page.setDefaultTimeout(1600);
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.goto(`http://127.0.0.1:${server.address().port}/`,{waitUntil:'load'});
  await page.waitForFunction(()=>window.layerInstrument&&window.spatialInstrument&&!window.layerInstrument.polling&&!window.spatialInstrument.polling);
  await run(page);
  assert.deepEqual(errors,[],'Uncaught UI exception');
  proof.checks.push({name,passed:true});
 }catch(error){proof.checks.push({name,passed:false,error:error.message.split('\n').slice(0,6).join('\n'),page_errors:errors});}
 finally{await page.close();}
}
const open=async(page,kind)=>{await page.locator('#open-'+kind).click();await page.locator('#'+kind+'-panel').waitFor({state:'visible'});await page.waitForFunction(name=>!window[name==='spatial'?'spatialInstrument':'layerInstrument'].polling,kind);};
const wait=async(page,fn)=>page.waitForFunction(fn,null,{timeout:1800});
async function main(){
 const playwright=require(options['--playwright']||process.env.COSMOS2_PLAYWRIGHT||'/home/an/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 browser=await playwright.chromium.launch({headless:true});
 context=await browser.newContext({viewport:{width:1920,height:1080}});
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.origin!==`http://127.0.0.1:${server.address().port}`){proof.unexpected_requests.push(url.origin+url.pathname);return route.abort();}
  return route.continue();
 });
 for(const kind of ['spatial','layers']){
  await test(kind+'-initial-outage-blocks-mutation',async page=>{
   await open(page,kind);
   assert(await page.locator('#'+kind+'-create').isDisabled(),'A disconnected panel must disable its source controls');
   assert(await page.locator('#'+kind+'-retry').isVisible(),'Connection retry must be visible');
   assert.match(await page.locator('#'+kind+'-status').textContent(),/conexão/i);
   assert.equal(fixture.posts.length,0);
  },()=>{fixture.fail=true;});
  await test(kind+'-retry-clears-only-transport-error',async page=>{
   await open(page,kind);assert.notEqual(await page.locator('#'+kind+'-error').textContent(),'');
   fixture.fail=false;await page.locator('#'+kind+'-retry').click();
   await wait(page,()=>!document.querySelector('[id$="-panel"]:not([hidden]) [role="alert"]').textContent);
   assert(!(await page.locator('#'+kind+'-create').isDisabled()),'Controls must recover');
   assert(await page.locator('#'+kind+'-retry').isHidden());
  },()=>{fixture.fail=true;});
  await test(kind+'-later-outage-blocks-stale-snapshot',async page=>{
   await open(page,kind);assert(!(await page.locator('#'+kind+'-create').isDisabled()));
   fixture.fail=true;
   await wait(page,()=>document.querySelector('[id$="-panel"]:not([hidden]) fieldset').disabled);
   assert(await page.locator('#'+kind+'-create').isDisabled());
   assert(await page.locator('#'+kind+'-retry').isVisible());
  });
  await test(kind+'-invalid-snapshot-is-recoverable',async page=>{
   await open(page,kind);assert(await page.locator('#'+kind+'-create').isDisabled());
   assert.match(await page.locator('#'+kind+'-error').textContent(),/incompleta|inválida/i);
   assert(await page.locator('#'+kind+'-retry').isVisible());
  },()=>{fixture.invalid=true;});
  await test(kind+'-sixteen-body-source-has-explicit-route',async page=>{
   await open(page,kind);
   assert.match(await page.locator('#'+kind+'-status').textContent(),/quatro corpos/);
   assert.equal(await page.evaluate(()=>window.fixtureCommands.length),0,'Opening must not replace the source');
   assert.equal(await page.evaluate(()=>appState.physics.bodies.length),16);
   await page.locator('#'+kind+'-atlas').click();
   await page.locator('#'+kind+'-copy').click();
   await wait(page,()=>appState.mode==='experiment'&&appState.physics.bodies.length===4);
   assert(!(await page.locator('#'+kind+'-create').isDisabled()));
   assert.deepEqual(await page.evaluate(()=>window.fixtureCommands.map(c=>c.endpoint)),['/api/command','/api/solar/experiment']);
  },()=>{fixture.app.physics.bodies.push(...Array.from({length:12},(_,i)=>({id:'extra-'+i,name:'Extra',reference_id:'fixture:'+i})));});
  await test(kind+'-running-source-can-be-paused',async page=>{
   await open(page,kind);assert.match(await page.locator('#'+kind+'-status').textContent(),/Pause/i);
   await page.locator('#'+kind+'-pause').click();
   await wait(page,()=>appState.physics.paused);
   assert(!(await page.locator('#'+kind+'-create').isDisabled()));
   assert.deepEqual(await page.evaluate(()=>window.fixtureCommands.map(c=>c.request.command)),['pause']);
  },()=>{fixture.app.physics.paused=false;});
 }
 await test('switching-panels-reclaims-space-and-aria-state',async page=>{
  await open(page,'layers');await open(page,'spatial');
  assert(await page.locator('#layers-panel').isHidden());
  assert.equal(await page.locator('#open-layers').getAttribute('aria-expanded'),'false');
  await page.keyboard.press('Escape');assert(await page.locator('#spatial-panel').isHidden());
  assert.equal(await page.evaluate(()=>document.activeElement.id),'open-spatial');
 });
 await test('mesh-recovery-hides-controls-without-an-artifact',async page=>{
  await open(page,'spatial');assert(await page.locator('#spatial-leave').isVisible());
  assert(await page.locator('#spatial-visible').isHidden()||await page.locator('#spatial-visible').isDisabled(),'A recovery without an artifact must not expose an operative visibility toggle');
  await page.locator('#spatial-leave').click();
  await wait(page,()=>!window.spatialInstrument.snapshot.recovery_required);
  assert.equal(fixture.posts.at(-1).body.command,'leave');
 },()=>{fixture.snapshots.spatial.recovery_required=true;});
 await test('mesh-lock-disables-keyboard-navigation-and-restores-it',async page=>{
  await open(page,'spatial');assert(await page.locator('#atlas').isDisabled(),'Pointer-only blocking leaves keyboard navigation live');
  await page.locator('#spatial-leave').click();
  await wait(page,()=>!document.getElementById('atlas').disabled);
  assert(!(await page.locator('#open-layers').isDisabled()));
 },()=>{fixture.snapshots.spatial.recovery_required=true;});
 await test('layers-recovery-keeps-leave-available',async page=>{
  await open(page,'layers');assert(await page.locator('#layers-leave').isVisible());
  await page.locator('#layers-leave').click();await wait(page,()=>!window.layerInstrument.snapshot.recovery_required);
  assert.equal(fixture.posts.at(-1).body.command,'leave');
 },()=>{fixture.snapshots.layers.recovery_required=true;});
 await test('domain-error-survives-successful-state-poll',async page=>{
  await open(page,'layers');const before=await page.evaluate(()=>JSON.stringify(appState.physics));
  await page.locator('#layers-create').click();
  await wait(page,()=>document.getElementById('layers-error').textContent.includes('fora do domínio'));
  assert.equal(await page.evaluate(()=>JSON.stringify(appState.physics)),before);
  assert.match(await page.locator('#layers-error').textContent(),/fora do domínio/);
 },()=>{fixture.commandError='Coordenadas fora do domínio do modelo.';});
 await test('new-imported-branch-remains-selected',async page=>{
  await open(page,'layers');await page.locator('#layers-import summary').click();
  await page.locator('#layers-import-file').setInputFiles({name:'composed.json',mimeType:'application/json',buffer:Buffer.from('{"fixture":"composed-reference"}')});
  await page.locator('#layers-import-preview').click();
  await page.locator('#layers-import-commit').click();
  await wait(page,()=>window.layerInstrument.snapshot.branches.length===2);
  assert.equal(await page.locator('#layers-branches').inputValue(),'new-branch');
 },()=>{fixture.snapshots.layers.branches=[{id:'old-branch',name:'Ramo anterior',valid:true}];});
 for(const scale of [100,150])for(const kind of ['spatial','layers']){
  await test(kind+'-scroll-and-controls-'+scale,async page=>{
   await page.setViewportSize({width:1280,height:720});
   if(scale===150)await page.evaluate(()=>document.body.classList.add('large-ui'));
   await open(page,kind);
   const box=await page.locator('#'+kind+'-panel').evaluate(node=>({scroll:node.scrollWidth,width:node.clientWidth,top:node.getBoundingClientRect().top,bottom:node.getBoundingClientRect().bottom,screen:innerHeight}));
   assert(box.scroll<=box.width+1,'Panel content overflows horizontally');
   assert(box.top>=0&&box.bottom<=box.screen,'Panel must fit the viewport');
   await page.locator('#'+kind+'-panel-close').click();
   await open(page,kind);
   const file=path.join(folder,kind+'-'+scale+'.png');await page.screenshot({path:file});
   proof.screenshots.push(path.relative(root,file).split(path.sep).join('/'));
  });
 }
 assert.deepEqual(proof.unexpected_requests,[]);
 assert(Object.entries(sources).every(([name,digest])=>sha(path.join(root,name))===digest),'Executed sources changed');
 proof.completed=true;
 const failed=proof.checks.filter(row=>!row.passed);
 proof.accepted=options['--expect-defects']?failed.length>0:failed.length===0;
 proof.expected_existing_defects=Boolean(options['--expect-defects']);
 proof.passed=proof.checks.length-failed.length;proof.failed=failed.length;
}
main().catch(error=>{proof.failure=error.stack;}).finally(async()=>{
 try{if(context)await context.close();if(browser)await browser.close();}
 catch(error){proof.cleanup_failure=String(error);proof.accepted=false;}
 await new Promise(resolve=>server.close(resolve));
 fs.writeFileSync(out,JSON.stringify(proof,null,2)+'\n');
 console.log(JSON.stringify({accepted:proof.accepted,completed:proof.completed,passed:proof.passed,failed:proof.failed,failures:proof.checks.filter(c=>!c.passed).map(c=>({name:c.name,error:c.error})),failure:proof.failure}));
 process.exitCode=proof.accepted?0:1;
});
