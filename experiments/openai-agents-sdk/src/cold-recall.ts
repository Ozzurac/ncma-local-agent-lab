import {readFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {freemem} from 'node:os';
import {Agent,Runner,MemorySession,setTracingDisabled,OpenAIChatCompletionsModel} from '@openai/agents';
import OpenAI from 'openai';
import {projectInstructions,loadSkill,LAB} from './framework.ts';
const ROOT=LAB;
const memory=resolve(ROOT,'bench','gptoss-framework','sessions','index-v2-mx-workflow_retry.json');
const saved=JSON.parse(readFileSync(memory,'utf8'));
if(saved.schema!=='ncma-session-v1'||!Array.isArray(saved.items)||saved.items.length<8)throw Error('COLD_MEMORY_UNAVAILABLE');
const entries=saved.items.length;
const session=new MemorySession({initialItems:saved.items});
const controller=new AbortController();
let reason='';
const monitor=setInterval(()=>{if(freemem()/1024**3<2.75){reason='RAM_GUARD';controller.abort();}},700);
const deadline=setTimeout(()=>{reason='WALL_GUARD';controller.abort();},190000);
setTracingDisabled(true);
async function main(){
 const p=await fetch('http://127.0.0.1:18991/props',{signal:AbortSignal.timeout(3000)});
 const props=await p.json() as any;
 if((props.default_generation_settings?.n_ctx??props.n_ctx)!==16384)throw Error('CTX_NOT_16K');
 const client=new OpenAI({apiKey:'local-no-secret',baseURL:'http://127.0.0.1:18991/v1',maxRetries:0,timeout:110000});
 const model=new OpenAIChatCompletionsModel(client,'ncma-gptoss');
 const agent=new Agent({name:'NCMA cold memory rehydration probe',
  instructions:projectInstructions()+'\n'+loadSkill('idempotency-retry-analysis')+'\nFor this specific memory test, do not use tools. Never claim tests executed.',
  model,tools:[],modelSettings:{maxTokens:3500}});
 const runner=new Runner({tracingDisabled:true});
 let reply='';let failure='';
 try{
  const response=await runner.run(agent,'From the PREVIOUS conversation stored in memory, name two Python source filenames you examined, the defect you found and the local knowledge module you consulted. Do not invent tests, do not open files, and do not use tools.',{session,maxTurns:2,signal:controller.signal});
  reply=String(response.finalOutput??'').trim();
 }catch(e){failure=String(e);}
 finally{clearInterval(monitor);clearTimeout(deadline);}
 const lower=reply.toLowerCase();
 const pass=reply.length>=110&&lower.includes('dispatch.py')&&lower.includes('ledger.py')&&(lower.includes('idempot')||lower.includes('retry'))&&!reason&&!failure;
 const report={coldResume:true,pass,itemsRestored:entries,reply,replyLength:reply.length,failure,reason,source:'file-backed MemorySession; no tools available to agent'};
 const file=resolve(ROOT,'bench','gptoss-framework','runs','cold-recall-mx-workflow_retry.json');
 writeFileSync(file,JSON.stringify(report,null,2));
 console.log(JSON.stringify({pass,itemsRestored:entries,replyLength:reply.length,reason,failure,reportPath:file}));
 if(!pass)process.exitCode=2;
}
main().catch(e=>{console.error(String(e));process.exitCode=3;});
