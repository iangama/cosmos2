'use strict';
// Isolated browser-state regression checks with real frozen model outputs.
// This server never calls a renderer or the owner's application process.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const opts=Object.fromEntries(process.argv.slice(2).map(value=>{const i=value.indexOf('=');return i<0?[value,true]:[value.slice(0,i),value.slice(i+1)];}));
const label=opts['--label'];assert(/^[a-z0-9-]+$/.test(label||''));
const product=path.resolve(root,opts['--product']||'output/original-flow-hotfix-product0.27.2');
const ui=path.join(product,'app/ui'),fixtures=path.join(root,'output/forces-confirmed-ui-fixtures-20261120a');
const out=path.join(root,'evidence',`forces-confirmed-ui-${label}.json`),folder=path.join(root,'output',`forces-confirmed-ui-${label}`);
assert(!fs.existsSync(out)&&!fs.existsSync(folder),'Preserve previous attempts');fs.mkdirSync(folder);
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex'),sha=file=>hash(fs.readFileSync(file));
const catalog=JSON.parse(fs.readFileSync(path.join(fixtures,'catalog.json'),'utf8'));
const records=Object.fromEntries(Object.keys(catalog.scenarios).map(key=>[key,JSON.parse(fs.readFileSync(path.join(fixtures,key+'.json'),'utf8'))]));
const fixtureProof=JSON.parse(fs.readFileSync(path.join(root,'evidence/forces-confirmed-ui-fixtures-20261120a.json'),'utf8'));
assert(fixtureProof.accepted&&fixtureProof.completed&&fixtureProof.cases.length===12);
const names=['forces.html','forces.css','forces.js','geomagnetism.js','fusion.js','decays.js'];
const sources=Object.fromEntries([...names.map(name=>path.join(ui,name)),__filename,...['catalog',...Object.keys(records)].map(name=>path.join(fixtures,name+'.json'))].map(file=>[path.relative(root,file).split(path.sep).join('/'),sha(file)]));
const clone=value=>JSON.parse(JSON.stringify(value));
let fixture;
function reset(){fixture={failNext:false,failCatalog:false,posts:[],saved:null};}
reset();
const proof={accepted:false,completed:false,native_user_flow_accepted:false,
 scope:'Headless browser state/scale checks only, using real frozen default scientific responses and a memory-only HTTP adapter. No original launcher, owner session, renderer, scientific recomputation, persistence or performance acceptance.',
 product:path.relative(root,product).split(path.sep).join('/'),source_sha256:sources,checks:[],captures:[],unexpected_requests:[]};
function reply(res,status,value,type='application/json'){
 res.writeHead(status,{'Content-Type':type,'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'"});
 res.end(type==='application/json'?JSON.stringify(value):value);
}
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://127.0.0.1'),route=url.pathname;
 if(route==='/api/forces/catalog')return reply(res,fixture.failCatalog?503:200,fixture.failCatalog?{ok:false,error:'Catálogo indisponível no teste.'}:catalog);
 if(route==='/api/geomagnetism/texture')return reply(res,200,fs.readFileSync(path.join(product,'data/textures/earth.jpg')),'image/jpeg');
 if(route.startsWith('/api/forces/')){
  let raw='';for await(const chunk of req)raw+=chunk;
  const body=JSON.parse(raw),action=route.slice('/api/forces/'.length);fixture.posts.push({action,body:clone(body)});
  if(action==='evaluate'){
   if(fixture.failNext){fixture.failNext=false;return reply(res,503,{ok:false,error:'Falha de recálculo simulada.'});}
   assert(records[body.scenario],body.scenario);return reply(res,200,records[body.scenario]);
  }
  if(action==='save'){fixture.saved=clone(body);return reply(res,200,{ok:true,saved:{configuration:body}});}
  if(action==='load')return fixture.saved?reply(res,200,{ok:true,configuration:fixture.saved,restoration:{status:'same_generation',differences:[],saved_schema:3}}):reply(res,400,{ok:false,error:'Não há condições salvas neste teste.'});
  if(action==='export')return reply(res,200,{...records[body.scenario],export_file:'memory-only-fixture-export.json'});
 }
 if(/^\/[a-z0-9.-]+\.(html|css|js)$/.test(route)){
  const file=path.join(ui,route.slice(1));if(fs.existsSync(file))return reply(res,200,fs.readFileSync(file),route.endsWith('.html')?'text/html; charset=utf-8':route.endsWith('.js')?'text/javascript':'text/css');
 }
 reply(res,404,{});
});
let browser,context;
async function test(name,run,options={}){
 reset();if(options.setup)options.setup();const page=await context.newPage();page.setDefaultTimeout(2200);
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.addInitScript(scale=>localStorage.setItem('cosmos2-ui-scale',scale),options.scale||'1');
  await page.goto(`http://127.0.0.1:${server.address().port}/forces.html`,{waitUntil:'load'});
  await page.waitForFunction(()=>typeof response!=='undefined'&&response?.ok&&!pending);
  await run(page);
  assert.deepEqual(errors,[],'Uncaught UI exception');proof.checks.push({name,passed:true});
 }catch(error){proof.checks.push({name,passed:false,error:error.message.split('\n').slice(0,8).join('\n'),stack:error.stack,page_errors:errors});}
 finally{await page.close();}
}
async function rejectScenario(page,key){
 fixture.failNext=true;await page.locator(`[data-scenario="${key}"]`).click();
 await page.waitForFunction(()=>!pending&&document.getElementById('force-status').classList.contains('error'));
}
async function main(){
 const {chromium}=require(opts['--playwright']||'/home/an/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));browser=await chromium.launch({headless:true});
 context=await browser.newContext({viewport:{width:1440,height:900}});
 await context.route('**/*',async route=>{const url=new URL(route.request().url());if(url.origin!==`http://127.0.0.1:${server.address().port}`){proof.unexpected_requests.push(url.origin+url.pathname);return route.abort();}return route.continue();});
 await test('rejected-scenario-keeps-confirmed-drawing-and-notice',async page=>{
  const before=hash(await page.evaluate(()=>JSON.stringify(response)));await rejectScenario(page,'strong');
  assert.equal(await page.evaluate(()=>config.scenario),'gravity');
  assert.equal(await page.evaluate(()=>response.configuration.scenario),'gravity');
  assert.equal(await page.locator('#scenarios .selected').getAttribute('data-scenario'),'strong','The draft remains editable');
  assert(await page.locator('#result-draft-note').isVisible());
  assert.equal(hash(await page.evaluate(()=>JSON.stringify(response))),before,'Confirmed response was mutated');
  await page.setViewportSize({width:1400,height:900});
 });
 await test('save-and-export-after-rejection-use-confirmed-result',async page=>{
  await rejectScenario(page,'strong');await page.locator('#save-forces').click();
  await page.waitForFunction(()=>!pending&&document.getElementById('force-status').textContent.includes('salv'));
  await page.locator('#export-forces').click();await page.waitForFunction(()=>!pending&&lastForcesExport?.ok);
  assert.equal(fixture.posts.find(row=>row.action==='save').body.scenario,'gravity');
  assert.equal(fixture.posts.find(row=>row.action==='export').body.scenario,'gravity');
  assert.equal(await page.evaluate(()=>lastForcesExport.physics_sha256),records.gravity.physics_sha256);
 });
 await test('restore-confirmed-conditions-without-recalculation',async page=>{
  await rejectScenario(page,'strong');const count=fixture.posts.filter(row=>row.action==='evaluate').length;
  await page.locator('#restore-result-conditions').click();
  assert.equal(await page.locator('#scenarios .selected').getAttribute('data-scenario'),'gravity');
  assert(await page.locator('#result-draft-note').isHidden());
  assert.equal(fixture.posts.filter(row=>row.action==='evaluate').length,count);
  assert.equal(await page.evaluate(()=>draftConfig.scenario),'gravity');
 });
 await test('successful-retry-publishes-the-new-result',async page=>{
  await rejectScenario(page,'strong');await page.locator('#calculate').click();
  await page.waitForFunction(()=>!pending&&response.configuration.scenario==='strong');
  assert.equal(await page.evaluate(()=>config.scenario),'strong');
  assert(await page.locator('#result-draft-note').isHidden());
  assert.equal(await page.evaluate(()=>response.physics_sha256),records.strong.physics_sha256);
 });
 await test('editing-a-field-does-not-mutate-confirmed-data',async page=>{
  const before=hash(await page.evaluate(()=>JSON.stringify(response)));
  const input=page.locator('#parameters input[type=number]').first();const current=Number(await input.inputValue());
  await input.fill(String(current===0?1:current*1.1));
  assert(await page.locator('#result-draft-note').isVisible());
  await page.locator('#save-forces').click();await page.waitForFunction(()=>!pending);
  assert.deepEqual(fixture.posts.find(row=>row.action==='save').body,records.gravity.configuration);
  assert.equal(hash(await page.evaluate(()=>JSON.stringify(response))),before);
 });
 await test('save-load-recalculates-and-reports-generation',async page=>{
  await page.locator('#save-forces').click();await page.waitForFunction(()=>!pending&&document.getElementById('force-status').textContent.includes('salv'));
  await page.locator('[data-scenario=strong]').click();await page.waitForFunction(()=>!pending&&response.configuration.scenario==='strong');
  await page.locator('#load-forces').click();await page.waitForFunction(()=>!pending&&response.configuration.scenario==='gravity');
  assert(await page.locator('#restoration-note').isVisible());assert.match(await page.locator('#restoration-note').innerText(),/correspondem/);
  assert.equal(await page.evaluate(()=>config.scenario),'gravity');
 });
 await test('all-twelve-default-scenarios-remain-renderable',async page=>{
  for(const key of Object.keys(records)){
   await page.locator(`[data-scenario="${key}"]`).click();
   await page.waitForFunction(key=>!pending&&response.configuration.scenario===key,key);
   assert.equal(await page.evaluate(()=>config.scenario),key);assert.equal(await page.evaluate(()=>response.physics_sha256),records[key].physics_sha256);
  }
 });
 for(const [scenario,choice] of [['fusion','mixture'],['decays','parent_case']])await test(scenario+'-failed-choice-preserves-visible-curves',async page=>{
  await page.locator(`[data-scenario="${scenario}"]`).click();await page.waitForFunction(key=>!pending&&response.configuration.scenario===key,scenario);
  const before=hash(await page.evaluate(()=>JSON.stringify(response))),selector=`#parameters [name="${choice}"]`;
  const values=await page.locator(selector+' option').evaluateAll(nodes=>nodes.map(node=>node.value));
  const selected=await page.locator(selector).inputValue(),other=values.find(value=>value!==selected);assert(other);
  fixture.failNext=true;await page.locator(selector).selectOption(other);await page.waitForFunction(()=>!pending&&document.getElementById('force-status').classList.contains('error'));
  await page.setViewportSize({width:1430,height:890});
  assert.equal(hash(await page.evaluate(()=>JSON.stringify(response))),before);
  assert(await page.evaluate(key=>visibleCurves.has(key),scenario));
  assert(await page.locator('#result-draft-note').isVisible());
 });
 for(const scale of ['1','1.25','1.5'])await test('shared-scale-'+scale,async page=>{
  assert.equal(await page.evaluate(()=>Number(getComputedStyle(document.body).zoom)),Number(scale));
  const layout=await page.evaluate(()=>{const a=document.querySelector('article'),r=a.getBoundingClientRect();return {scroll:a.scrollWidth,client:a.clientWidth,top:r.top,bottom:r.bottom,height:innerHeight}});
  assert(layout.scroll<=layout.client+1,'Article overflows horizontally');
  const file=path.join(folder,'scale-'+scale.replace('.','-')+'.png');await page.screenshot({path:file});proof.captures.push(path.relative(root,file).split(path.sep).join('/'));
 },{scale});
 assert.deepEqual(proof.unexpected_requests,[]);assert(Object.entries(sources).every(([name,digest])=>sha(path.join(root,name))===digest));
 const failed=proof.checks.filter(row=>!row.passed);proof.completed=true;proof.passed=proof.checks.length-failed.length;proof.failed=failed.length;
 proof.expected_existing_defects=Boolean(opts['--expect-defects']);proof.accepted=proof.expected_existing_defects?failed.length>0:failed.length===0;
}
main().catch(error=>{proof.failure=error.stack;}).finally(async()=>{
 try{if(context)await context.close();if(browser)await browser.close();}catch(error){proof.cleanup_failure=String(error);proof.accepted=false;}
 await new Promise(resolve=>server.close(resolve));fs.writeFileSync(out,JSON.stringify(proof,null,2)+'\n');
 console.log(JSON.stringify({accepted:proof.accepted,completed:proof.completed,passed:proof.passed,failed:proof.failed,failures:proof.checks.filter(row=>!row.passed).map(row=>({name:row.name,error:row.error})),failure:proof.failure}));process.exitCode=proof.accepted?0:1;
});
