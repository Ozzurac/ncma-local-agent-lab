import {readFileSync,writeFileSync,appendFileSync,mkdirSync,copyFileSync,realpathSync} from 'node:fs';
import {resolve} from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import {freemem} from 'node:os';
import OpenAI from 'openai';
import {z} from 'zod';
import {Agent,Runner,MemorySession,tool,setTracingDisabled,OpenAIChatCompletionsModel} from '@openai/agents';
import {projectInstructions,loadSkill,readKb,searchKb} from './framework.ts';

const ROOT=(process.env.NCMA_LAB_ROOT ?? process.cwd()), BASE=resolve(ROOT,'bench','gptoss-g2');
const args=process.argv.slice(2);
if(args.length!==2||!args.includes('--variant=mx')||!args.includes('--case=workflow_retry'))throw Error('G2_FIX_REQUIRES_MX_WORKFLOW');
const parent=realpathSync(resolve(BASE,'proposals','mx-workflow_retry-6b4eabda-fd1'));
const trustedTests=realpathSync(resolve(BASE,'baseline','workflow_retry','tests','test_dispatch.py'));
const testLog=realpathSync(resolve(BASE,'verified_runs','mx-workflow_retry-6b4eabda-fd1-review2.tests.log'));
const sources={
 'src/dispatch.py':realpathSync(resolve(parent,'src','dispatch.py')),
 'src/ledger.py':realpathSync(resolve(parent,'src','ledger.py')),
 'tests/test_dispatch.py':trustedTests,
 'tests/last_test_result.log':testLog,
} as const;
const id='mx-workflow_retry-fix-'+randomUUID().slice(0,12);
const proposal=resolve(realpathSync(resolve(BASE,'proposals')),id);
mkdirSync(resolve(proposal,'src'),{recursive:true});
copyFileSync(sources['src/ledger.py'],resolve(proposal,'src','ledger.py'));
const hashLedger=createHash('sha256').update(readFileSync(sources['src/ledger.py'])).digest('hex');
const eventFile=resolve(realpathSync(resolve(BASE,'stage-logs')),id+'.jsonl');
writeFileSync(eventFile,'',{flag:'wx'});
const emit=(x:Record<string,unknown>)=>appendFileSync(eventFile,JSON.stringify({utc:new Date().toISOString(),...x}).slice(0,7000)+'\n');
const readPaths=new Set<string>();
let patched=false,minFree=100,stopped='',error='',reply='';
async function preflight(){
 for(const ep of ['/health','/v1/models','/props']){
  const r=await fetch('http://127.0.0.1:18991'+ep,{signal:AbortSignal.timeout(4000)});
  if(!r.ok)throw Error('SERVER_ERROR');
  const o=await r.json() as any;
  if(ep==='/health'&&o.status!=='ok')throw Error('NO_HEALTH');
  if(ep==='/v1/models'&&!o.data?.some((m:any)=>m.id==='ncma-gptoss'))throw Error('MODEL_ALIAS');
  if(ep==='/props'&&(o.default_generation_settings?.n_ctx??o.n_ctx)!==16384)throw Error('CTX_NOT_16K');
 }
}
async function main(){
 await preflight();
 if(freemem()/1024**3<5)throw Error('RAM_LOW');
 setTracingDisabled(true);
 const ctrl=new AbortController();
 const watch=setInterval(()=>{minFree=Math.min(minFree,freemem()/1024**3);if(minFree<2.75){stopped='RAM_GUARD';ctrl.abort();}},750);
 const wall=setTimeout(()=>{stopped='WALL_190S';ctrl.abort();},190000);
 const readTool=tool({name:'read_file',description:'Read a fixed source, trusted tests, or the independent test failure log, with no writes.',parameters:z.object({path:z.string()}),async execute({path}){
  const p=sources[path as keyof typeof sources];
  if(!p)throw Error('READ_PATH_DENIED');
  const data=readFileSync(p,'utf8');if(data.length>18000)throw Error('FILE_TOO_LONG');
  readPaths.add(path);emit({event:'read',path,chars:data.length});
  return 'FILE '+path+'\n'+data;
 }});
 const stage=tool({name:'submit_patch',description:'Stage a COMPLETE corrected src/dispatch.py source file only. The ledger.py proposal remains as previously generated. This does not execute code.',parameters:z.object({path:z.literal('src/dispatch.py'),content:z.string().min(40).max(7000)}),async execute({path,content}){
  if(content.includes('\0'))throw Error('NUL_DENIED');
  writeFileSync(resolve(proposal,'src','dispatch.py'),content,'utf8');
  patched=true;emit({event:'patch_staged',path,chars:content.length});
  return 'SOURCE_STAGED_NOT_TESTED';
 }});

 const selected=searchKb('idempotency retry delivery');
 if(!selected.length||selected[0].id!=='reliability-idempotency')throw Error('KB_SELECTION_MISMATCH');
 const knowledge=readKb(selected[0].id),skill=loadSkill('idempotency-retry-analysis');
 emit({event:'framework_preload',skill:'idempotency-retry-analysis',kb:knowledge.id,originalLedgerSha:hashLedger});
 const client=new OpenAI({apiKey:'local-no-secret',baseURL:'http://127.0.0.1:18991/v1',maxRetries:0,timeout:155000});
 const model=new OpenAIChatCompletionsModel(client,'ncma-gptoss');
 const instructions=projectInstructions()+'\n\nREQUIRED SKILL:\n'+skill+
  '\n\nREQUIRED KB MODULE (indexed, SHA256 verified):\n'+knowledge.text+
  '\n\nG2 repair continuation: You previously created a candidate patch that passed 9 of 10 tests. The verified independent test found one bug: a failed delivery leaves last_error="network" even after a later successful retry. Preserve event identity and attempts, but clear last_error after successful recovery. Use read_file for existing candidate source and the independent log. Submit a FULL fixed src/dispatch.py using submit_patch. Do not modify src/ledger.py, original files, or tests. No shell or test execution by you. No claim of PASS.';
 const agent=new Agent({name:'NCMA G2 iterative repair follow-up',instructions,model,tools:[readTool,stage],modelSettings:{maxTokens:6144}});
 const runner=new Runner({tracingDisabled:true});
 const session=new MemorySession();
 const prompt='Iterate on your prior patch based on the real failed test. First use read_file for src/dispatch.py, src/ledger.py, tests/test_dispatch.py and tests/last_test_result.log. Then submit_patch with complete revised src/dispatch.py to fix last_error not cleared after successful retry, without changing the already staged ledger.py. Keep source import/class/function signatures stable. Your task is to propose code only; a separate validator will run the tests.';
 try{
  emit({event:'preflight',runId:id,sourceCase:'9_of_10_fail_last_error',ctx:16384,model:'mx',freeGiB:freemem()/1024**3});
  const result=await runner.run(agent,prompt,{session,maxTurns:7,signal:ctrl.signal});
  reply=String(result.finalOutput??'');
  emit({event:'model_final',answer:reply.slice(0,1500)});
 }catch(e){error=String(e);emit({event:'sdk_error',error});}
 finally{clearInterval(watch);clearTimeout(wall);}
 const valid=!error&&!stopped&&patched&&readPaths.has('src/dispatch.py')&&readPaths.has('tests/last_test_result.log');
 const report={runId:id,stagePass:valid,error,stopped,patched,proposalDir:proposal,previousProposalDir:parent,readPaths:[...readPaths],modelAnswer:reply,requiredSkill:'idempotency-retry-analysis',kbId:knowledge.id,ledgerSha256:hashLedger,minFreeGiB:Number(minFree.toFixed(3)),trace:eventFile};
 const file=resolve(realpathSync(resolve(BASE,'stage-logs')),id+'.json');
 writeFileSync(file,JSON.stringify(report,null,2),'utf8');
 emit({event:'stage_closeout',pass:valid,reportFile:file});
 console.log(JSON.stringify({stagePass:valid,runId:id,proposalDir:proposal,readPaths:[...readPaths],patched,modelError:error,minFreeGiB:report.minFreeGiB,reportFile:file}));
 if(!valid)process.exitCode=2;
}
main().catch(e=>{console.error('G2_FIX_FATAL',String(e));process.exitCode=3;});
