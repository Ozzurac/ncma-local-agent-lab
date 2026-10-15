import {readFileSync, realpathSync, writeFileSync, appendFileSync, existsSync} from 'node:fs';
import {resolve, relative, sep} from 'node:path';
import {randomUUID} from 'node:crypto';
import {freemem} from 'node:os';
import OpenAI from 'openai';
import {projectInstructions,loadSkill,searchKb,readKb} from './framework.ts';
import {z} from 'zod';
import {Agent, Runner, MemorySession, tool, setTracingDisabled, OpenAIChatCompletionsModel} from '@openai/agents';

const ROOT=(process.env.NCMA_LAB_ROOT ?? process.cwd());
const SERVER='http://127.0.0.1:18991';
const ALIAS='ncma-gptoss';
const GiB=1024**3;
const freeGiB=()=>freemem()/GiB;
const args=process.argv.slice(2);
const variant=args.find(s=>s.startsWith('--variant='))?.slice(10);
const caseName=args.find(s=>s.startsWith('--case='))?.slice(7);
if(args.length!==2 || !['mx','ud'].includes(String(variant)) || !['workflow_retry','nested_config'].includes(String(caseName)))throw Error('BAD_ARGS');

const caseSpecs={
 workflow_retry:{
  doc:'qwen-eval/workflow_retry/docs/README.txt',
  sources:['qwen-eval/workflow_retry/src/dispatch.py','qwen-eval/workflow_retry/src/ledger.py','qwen-eval/workflow_retry/tests/test_dispatch.py'],
  topic:'safe idempotent event dispatcher, retries, attempts, matching payload',
  clues:[['idempot'],['attempt','tentativ'],['payload'],['falh','failed','except','error'],['duplic','duplicate']]
 },
 nested_config:{
  doc:'qwen-eval/nested_config/docs/AGENT_NOTE.txt',
  sources:['qwen-eval/nested_config/src/merge.py','qwen-eval/nested_config/src/settings.py','qwen-eval/nested_config/tests/test_config.py'],
  topic:'deep merge, base env cli priority, zero and false, schema validation',
  clues:[['deep_merge'],['update','raso','superficial','recurs','aninhad'],['false','falso'],['zero',' 0','=0'],['schema','desconhec','unknown']]
 }
} as const;
const spec=caseSpecs[caseName as keyof typeof caseSpecs];
const norm=(x:string)=>x.replace(/\\/g,'/').toLowerCase();
const allAllowed=new Set<string>([...spec.sources,spec.doc].map(norm));
const runDir=realpathSync(resolve(ROOT,'bench','gptoss-framework','runs'));
const evidencePath=resolve(runDir,String(variant)+'-'+String(caseName)+'-'+new Date().toISOString().replace(/[:.]/g,'-')+'-'+randomUUID().slice(0,8)+'.jsonl');
writeFileSync(evidencePath,'',{flag:'wx'});
const emit=(data:Record<string,unknown>)=>appendFileSync(evidencePath,JSON.stringify({utc:new Date().toISOString(),...data}).slice(0,26000)+'\n');
const reads=new Set<string>();
let kbCount=0;
let minFree=100;
function trustedFile(pathValue:string):{rel:string,abs:string}{
 const candidate=resolve(ROOT,pathValue);
 const actual=realpathSync(candidate);
 const base=realpathSync(ROOT);
 const inside=actual.toLowerCase()===base.toLowerCase()||actual.toLowerCase().startsWith(base.toLowerCase()+sep);
 if(!inside)throw Error('TOOL_PATH_OUTSIDE_LAB');
 const rel=norm(relative(base,actual));
 if(!allAllowed.has(rel))throw Error('TOOL_PATH_NOT_IN_CASE_ALLOWLIST_'+rel);
 return {rel,abs:actual};
}
async function verifyServer(){
 const health=await fetch(SERVER+'/health',{signal:AbortSignal.timeout(3000)});
 if(!health.ok||(await health.json() as any).status!=='ok')throw Error('SERVER_UNHEALTHY');
 const models=await fetch(SERVER+'/v1/models',{signal:AbortSignal.timeout(3000)});
 if(!models.ok||!(await models.json() as any).data?.some((m:any)=>m.id===ALIAS))throw Error('MODEL_ALIAS_MISMATCH');
 const props=await fetch(SERVER+'/props',{signal:AbortSignal.timeout(3000)});
 const p=await props.json() as any;
 if((p.default_generation_settings?.n_ctx??p.n_ctx)!==16384)throw Error('SERVER_CONTEXT_NOT_16K');
}
async function main(){
 await verifyServer();
 if(freeGiB()<5)throw Error('READY_RAM_BELOW_5GIB');
 setTracingDisabled(true);
 const controller=new AbortController();
 let aborted='';
 const periodic=setInterval(()=>{
  const val=freeGiB();minFree=Math.min(minFree,val);
  if(val<2.75){aborted='RAM_GUARD';controller.abort();}
 },650);
 const deadline=setTimeout(()=>{aborted='WALL_190S';controller.abort();},190000);
 const readTool=tool({
  name:'read_file',
  description:'Read source or test file in the authorized NCMA fixture. Never run code and never modify files. Supply lab-relative path.',
  parameters:z.object({path:z.string()}),
  async execute({path}){
   const target=trustedFile(path);
   if(norm(target.rel)===norm(spec.doc))throw Error('USE_KB_LOOKUP_FOR_DOCUMENT');
   const content=readFileSync(target.abs,'utf8');
   if(content.length>17000)throw Error('SOURCE_TOO_LARGE');
   reads.add(target.rel);
   emit({event:'read_file',path:target.rel,bytes:content.length});
   return 'SOURCE '+target.rel+'\n'+content;
  }
 });
 const kbTool=tool({
  name:'lookup_project_kb',
  description:'Look up the authoritative local project description/requirements for the selected case. This is a read-only local KB document, not a web search.',
  parameters:z.object({topic:z.string()}),
  async execute({topic}){
   const target=trustedFile(spec.doc);
   const content=readFileSync(target.abs,'utf8');
   kbCount++;
   emit({event:'kb_lookup',topic:topic.slice(0,100),path:target.rel,bytes:content.length});
   return 'LOCAL_KB '+target.rel+'\n'+content;
  }
 });
 const loadedSkills:string[]=[];
 const readModules:string[]=[];
 let searchCount=0;
 const skillTool=tool({name:'load_skill',description:'Load exactly one specialized Skill from persistent .agents/skills by name.',parameters:z.object({name:z.string()}),
 async execute({name}){const value=loadSkill(name);loadedSkills.push(name);emit({event:'skill_loaded',name,bytes:value.length});return value;}});
 const searchTool=tool({name:'search_knowledge',description:'Query local modular knowledge index, returning module IDs.',parameters:z.object({query:z.string()}),
 async execute({query}){const value=searchKb(query);searchCount++;emit({event:'kb_index_search',query,matches:value.map(x=>x.id)});return JSON.stringify(value);}});
 const moduleTool=tool({name:'read_knowledge',description:'Read one SHA256-verified local modular knowledge doc by its indexed ID.',parameters:z.object({id:z.string()}),
 async execute({id}){const doc=readKb(id);readModules.push(id);emit({event:'kb_module_read',id,bytes:doc.text.length});return doc.text;}});

 const client=new OpenAI({apiKey:'local-no-secret',baseURL:SERVER+'/v1',maxRetries:0,timeout:90000});
 const model=new OpenAIChatCompletionsModel(client,ALIAS);
 const requiredSkill=caseName==='workflow_retry'?'idempotency-retry-analysis':'config-merge-analysis';
 const requiredSkillText=loadSkill(requiredSkill);
 emit({event:'skill_preloaded',name:requiredSkill,bytes:requiredSkillText.length});
 const agent=new Agent({
  name:'NCMA ReadOnly Code Analyst',
   instructions:projectInstructions()+'\n\nMANDATORY SPECIALIZED SKILL (loaded by SDK framework from disk, not an optional model call):\n'+requiredSkillText+'\nSDK runtime: Load relevant Skill via load_skill, search the indexed KB via search_knowledge then read_knowledge, and read all source and test files with read_file. Report in PT-BR. No execution or file edits.',
  model,
  tools:[readTool,skillTool,searchTool,moduleTool],
  modelSettings:{maxTokens:4096}
 });
 const runner=new Runner({tracingDisabled:true});
 const sessionsDir=realpathSync(resolve(ROOT,'bench','gptoss-framework','sessions'));
 const sessionPath=resolve(sessionsDir,'index-v2-'+String(variant)+'-'+String(caseName)+'.json');
 const persisted=existsSync(sessionPath)?JSON.parse(readFileSync(sessionPath,'utf8')):null;
 if(persisted && (persisted.schema!=='ncma-session-v1'||!Array.isArray(persisted.items)||persisted.items.length>38))throw Error('MEMORY_STORE_INVALID');
 const previousItems=persisted?.items?.length??0;
 const session=new MemorySession({initialItems:persisted?.items??[]});
 let answer='';
 let memoryReply='';
 let rawUsage:any=null;
 let failure='';
 try{
  emit({event:'preflight',variant,caseName,ctx:16384,model:ALIAS,sourceCount:spec.sources.length,agentSdk:'0.20.0',format:'harmony-chat-completions',memory:'MemorySession isolated',knowledge:'local read-only docs',freeGiB:freeGiB()});
  const prompt='NCMA framework evaluation case '+String(caseName)+'. Follow the permanent project policy, use the matching specialized Skill and indexed KB module. First use search_knowledge to find the relevant module and read_knowledge to open it for the case: '+spec.topic+'. Then use read_file to read ALL three paths: '+spec.sources.join(' ; ')+'. Diagnose the concrete bugs, expected behavior per tests and a minimal correction proposal, using evidence and filenames. Do not execute code or claim the tests passed.';
  const result=await runner.run(agent,prompt,{session,maxTurns:9,signal:controller.signal});
  answer=String(result.finalOutput??'').trim();
  rawUsage=(result as any).rawResponses?.map((resp:any)=>resp.usage);
  emit({event:'initial_complete',answerLength:answer.length,readFiles:[...reads],kbCount,rawUsage,answer:answer.slice(0,13500)});
  if(answer.length>=180){
   const follow=await runner.run(agent,'Usando SOMENTE sua memoria da conversa anterior, sem consultar ferramentas novamente, diga em duas frases quais arquivos examinou e qual defeito central encontrou. Nao invente testes executados.',{session,maxTurns:3,signal:controller.signal});
   memoryReply=String(follow.finalOutput??'').trim();
   emit({event:'memory_followup',answer:memoryReply.slice(0,2500),length:memoryReply.length,historyItems:(await session.getItems()).length});
  }
 }catch(e){failure=String(e);emit({event:'sdk_error',error:failure});}
 finally{clearInterval(periodic);clearTimeout(deadline);}
 const lower=answer.toLowerCase();
 const score=spec.clues.map(words=>words.some(word=>lower.includes(word)));
 const missing=spec.sources.filter(s=>!reads.has(norm(s)));
 const reasons:string[]=[];
 if(failure)reasons.push('SDK_EXCEPTION');
 if(aborted)reasons.push(aborted);
 if(answer.length<180)reasons.push('NO_SUBSTANTIVE_FINAL_ANSWER');
 if(missing.length)reasons.push('MISSING_VERIFIED_SOURCE_READS');
 if(readModules.length<1)reasons.push('NO_KNOWLEDGE_RETRIEVAL');
 if(!requiredSkillText||!requiredSkill)reasons.push('SKILL_NOT_LOADED');
 if(searchCount<1)reasons.push('KB_INDEX_NOT_QUERIED');
 if(readModules.length<1)reasons.push('KB_MODULE_NOT_OPENED');
 if(!readModules.includes(caseName==='workflow_retry'?'reliability-idempotency':'software-configuration'))reasons.push('RELEVANT_KB_MODULE_MISSING');
 if(score.filter(Boolean).length<3)reasons.push('NOT_ENOUGH_DIAGNOSTIC_EVIDENCE');
 if(spec.sources.filter(s=>lower.includes(s.split('/').at(-1)!.toLowerCase())).length<2)reasons.push('MISSING_FILE_CITATIONS');
 let storedItems=0;
 if(answer.length>=180 && !failure && !aborted && requiredSkillText.length>0 && searchCount>0 && readModules.length>0 && reads.size===spec.sources.length){
  const items=await session.getItems();
  const contents=JSON.stringify({schema:'ncma-session-v1',items,updated:new Date().toISOString()});
  if(items.length<=38 && contents.length<180000){
   writeFileSync(sessionPath,contents,'utf8');
   storedItems=items.length;
   emit({event:'memory_persisted',previousItems,storedItems});
  }else emit({event:'memory_not_saved',itemCount:items.length,size:contents.length});
 }
 const memoryPass=memoryReply.length>=50&&(memoryReply.toLowerCase().includes('py')||memoryReply.toLowerCase().includes('arquivo'));
 const report={variant,caseName,pass:reasons.length===0,memoryPass,reasons,readFiles:[...reads],missing,kbCount,requiredSkill,loadedSkills,searchCount,readModules,previousItems,storedItems,answer,answerLength:answer.length,memoryReply,usage:rawUsage,minFreeGiB:Number(minFree.toFixed(3)),endFreeGiB:Number(freeGiB().toFixed(3)),error:failure,evidencePath};
 const reportPath=resolve(runDir,String(variant)+'-'+String(caseName)+'-latest.json');
 writeFileSync(reportPath,JSON.stringify(report,null,2));
 emit({event:'closeout',pass:report.pass,memoryPass,reasons,reportPath,freeGiB:freeGiB()});
 console.log(JSON.stringify({variant,caseName,pass:report.pass,memoryPass,reasons,readFiles:reads.size,kbCount,requiredSkill,loadedSkills,searchCount,readModules,answerLength:answer.length,minFreeGiB:report.minFreeGiB,evidencePath,reportPath,error:failure.slice(0,500)}));
 if(!report.pass)process.exitCode=2;
}
main().catch(e=>{console.error('AB_FATAL',String(e));process.exitCode=3;});
