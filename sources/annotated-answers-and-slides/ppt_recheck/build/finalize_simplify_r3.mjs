import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import crypto from 'node:crypto';

const [rootArg,candidateArg,volumesArg]=process.argv.slice(2);
const root=path.resolve(rootArg),candidate=path.resolve(candidateArg);
const skill='/root/.codex/skills/builtins/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const records=JSON.parse(await fs.readFile(path.join(candidate,'qa_package.json'),'utf8'));
const selected=volumesArg?new Set(volumesArg.split(',').map(Number)):null;
await fs.mkdir(path.join(root,'qa_r3'),{recursive:true});
await fs.mkdir(path.join(root,'validated_r3'),{recursive:true});
const receipts=[];
for(const rec of records){
 const name=path.basename(rec.output),volume=Number(name.match(/第(\d+)册/)[1]);
 if(selected&&!selected.has(volume))continue;
 const referencePath=path.join(root,'..','bundle','讲解课件',name);
 const referenceSha256=sha(await fs.readFile(referencePath));
 const result=await finalizePresentation({
  workspaceDir:root,candidatePath:path.join(candidate,name),
  finalPath:path.join(root,'validated_r3',name),
  pythonExecutable:process.env.CODEX_PRIMARY_RUNTIME_PYTHON,
  integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
  layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  explicitTotalSlideCount:rec.total_slides,
  requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'reference',families:['Droid Sans Fallback'],referencePath,referenceSha256},
  verifyArtifactToolImport:true,
  receiptPath:path.join(root,'qa_r3','finalizer_v'+volume+'.json')
 });
 receipts.push(result);
 console.log(JSON.stringify({volume,result}));
}
await fs.writeFile(path.join(root,'qa_r3','finalizer_all.json'),JSON.stringify(receipts,null,2));
