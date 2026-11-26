// Execute the actual calculate() function with deterministic transport/DOM fixtures.
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import path from 'node:path';
const root=process.cwd();
const seal=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const fixturePath='output/c214-orbits-native-20261114b/last-result.json';
const fixture=JSON.parse(fs.readFileSync(fixturePath,'utf8'));
const out='evidence/c214-ui-cancel-state-20261114a.json';
if(fs.existsSync(out))throw Error('Preserve existing receipt');
const trials=[];
for(const [version,sourcePath] of [['0.28.1','output/c214-orbits-product0.28.1/app/ui/forces.js'],['0.28.2','output/c214-orbits-product0.28.2/app/ui/forces.js']]){
  const source=fs.readFileSync(sourcePath,'utf8');
  const begin=source.indexOf('async function calculate(){'),end=source.indexOf('\nfunction renderResult(){',begin);
  if(begin<0||end<begin)throw Error('Actual calculate() source unavailable');
  const sandbox={structuredClone,fixture};vm.createContext(sandbox);
  const prelude=`let config=structuredClone(fixture.configuration),response,pending=false,animating=false,calls=0;
const form={reportValidity:()=>true,elements:[]},nodes={'parameters':form,'restoration-note':{},'time-index':{},animate:{}};
const byId=id=>nodes[id]||(nodes[id]={});
function buildParameters(){form.elements=Object.entries(config.parameters).map(([name,value])=>({name,value,tagName:typeof value==='string'?'SELECT':'INPUT'}));}
function buildControls(){}function buildEffects(){}function updateTimelikeParameters(){}function renderResult(){}function status(){}
function lock(v){pending=v;}function lastTimeIndex(){return response.result.time_s.length-1;}
async function calculateTimelike(){if(++calls===1)return structuredClone(fixture);const error=Error('Cancelled fixture');error.cancelled=true;throw error;}
function post(){throw Error('Unexpected synchronous transport');}
buildParameters();`;
  const run=`(async()=>{await calculate();const before=JSON.stringify(response),initial_alias=config===response.configuration;
form.elements.find(e=>e.name==='mass_solar').value=9.99;await calculate();
return {initial_alias,full_result_preserved:before===JSON.stringify(response),configuration_matches:JSON.stringify(config)===JSON.stringify(response.configuration),form_mass:Number(form.elements.find(e=>e.name==='mass_solar').value),completed_mass:response.configuration.parameters.mass_solar};})()`;
  const result=await vm.runInContext(prelude+source.slice(begin,end)+'\n'+run,sandbox);
  trials.push({version,source:sourcePath,source_sha256:seal(sourcePath),...result});
}
if(trials[0].full_result_preserved||!trials[0].initial_alias)throw Error('Regression did not reproduce on B');
if(!trials[1].full_result_preserved||trials[1].initial_alias||!trials[1].configuration_matches||trials[1].form_mass!==trials[1].completed_mass)throw Error('Revision C failed cancellation identity');
const proof={accepted:true,completed:true,scope:'Actual UI calculate() with deterministic cancelled transport and DOM fixtures; native proof remains separate',fixture:fixturePath,fixture_sha256:seal(fixturePath),script_sha256:seal(path.relative(root,new URL(import.meta.url).pathname)),trials};
fs.writeFileSync(out,JSON.stringify(proof,null,2)+'\n');
process.stdout.write(JSON.stringify({accepted:true,regression_reproduced:true,revision_c_preserved:true})+'\n');
