import {readFileSync,readdirSync,realpathSync,statSync} from 'node:fs';
import {resolve,relative,sep} from 'node:path';
import {createHash} from 'node:crypto';
export const LAB=(process.env.NCMA_LAB_ROOT ?? process.cwd());
const ROOT=realpathSync(LAB);
export function guardedRead(path:string,max=16000):string{
 const full=realpathSync(resolve(path));
 const actual=process.platform==='win32'?full.toLowerCase():full;
 const root=process.platform==='win32'?ROOT.toLowerCase():ROOT;
 if(actual!==root&&!actual.startsWith(root+sep))throw Error('OUTSIDE_LAB');
 if(statSync(full).size>max*3)throw Error('TOO_LARGE');
 const content=readFileSync(full,'utf8');
 if(content.length>max)throw Error('TOO_LONG');
 return content;
}
export function skills(){
 const dir=resolve(LAB,'.agents','skills');
 return readdirSync(dir,{withFileTypes:true}).filter(e=>e.isDirectory()&&/^[a-z0-9-]+$/.test(e.name)).map(e=>{
  const text=guardedRead(resolve(dir,e.name,'SKILL.md'));
  const h=/^---\r?\n([\s\S]*?)\r?\n---/.exec(text)?.[1];
  const name=h&&/^name: ([^\r\n]+)/m.exec(h)?.[1];
  const description=h&&/^description: ([^\r\n]+)/m.exec(h)?.[1];
  if(!name||name!==e.name||!description)throw Error('INVALID_SKILL_'+e.name);
  return {name,description};
 });
}
export function loadSkill(id:string){
 const item=skills().find(s=>s.name===id);
 if(!item)throw Error('UNKNOWN_SKILL');
 return guardedRead(resolve(LAB,'.agents','skills',id,'SKILL.md'));
}
export function kbIndex(){
 const value=JSON.parse(guardedRead(resolve(LAB,'knowledge','index.json')));
 if(value.schema!=='ncma-knowledge-index-v1'||!Array.isArray(value.modules))throw Error('INVALID_KB');
 return value.modules as Array<{id:string,path:string,title:string,keywords:string[],sha256:string}>;
}
export function searchKb(question:string){
 if(!question||question.length>240)throw Error('BAD_QUERY');
 const words=question.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().split(/[^a-z0-9]+/).filter(w=>w.length>2);
 return kbIndex().map(d=>{
  const text=(d.id+' '+d.title+' '+d.keywords.join(' ')).toLowerCase();
  return {id:d.id,title:d.title,score:words.reduce((n,w)=>n+(text.includes(w)?1:0),0)};
 }).filter(d=>d.score>0).sort((a,b)=>b.score-a.score).slice(0,5);
}
export function readKb(id:string){
 const doc=kbIndex().find(d=>d.id===id);
 if(!doc||!/^modules\/[a-z0-9-]+\/[a-z0-9-]+\.md$/.test(doc.path))throw Error('UNKNOWN_KB');
 const path=resolve(LAB,'knowledge',doc.path);
 const bytes=readFileSync(realpathSync(path));
 if(createHash('sha256').update(bytes).digest('hex')!==doc.sha256)throw Error('KB_SHA_MISMATCH');
 return {id,title:doc.title,text:guardedRead(path)};
}
export function projectInstructions(){
 const policy=guardedRead(resolve(LAB,'AGENTS.md'),12000);
 if(!policy.includes('2.75 GiB'))throw Error('POLICY_MISSING');
 return policy+'\nSkill catalog (select skill via load_skill when relevant):\n'+skills().map(s=>s.name+': '+s.description).join('\n');
}
export function readSource(path:string,allowed:string[]){
 if(typeof path!=='string'||path.includes('..')||/^[a-z]:/i.test(path)||path.startsWith('/')||path.startsWith('\\'))throw Error('INVALID_SOURCE_PATH');
 const norm=path.replace(/\\/g,'/').toLowerCase();
 if(!allowed.some(a=>a.toLowerCase()===norm))throw Error('NOT_ALLOWED_SOURCE');
 return guardedRead(resolve(LAB,path),17000);
}
