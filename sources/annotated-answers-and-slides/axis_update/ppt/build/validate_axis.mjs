import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root=path.resolve('axis_revision/ppt');
const skill='/root/.codex/skills/builtins/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(path.join(root,'validated'),{recursive:true});
await fs.mkdir(path.join(root,'qa'),{recursive:true});
for(const [v,count]of[[4,462],[5,430]]){
 const name=`小学四上同步素养卷第${v}册讲解课件答案.pptx`;
 const referencePath=path.resolve('axis_revision/bundle/讲解课件',name);
 const referenceSha256=crypto.createHash('sha256').update(await fs.readFile(referencePath)).digest('hex');
 const result=await finalizePresentation({workspaceDir:root,candidatePath:path.join(root,'final',name),finalPath:path.join(root,'validated',name),pythonExecutable:process.env.CODEX_PRIMARY_RUNTIME_PYTHON,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:count,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'reference',families:['Droid Sans Fallback'],referencePath,referenceSha256},verifyArtifactToolImport:true,receiptPath:path.join(root,'qa',`finalizer_v${v}.json`)});
 console.log(JSON.stringify({volume:v,finalSha256:result.finalSha256,slideCount:result.firstPartyImport?.slideCount,packageStatus:result.packageIntegrity?.status,layoutFindingCount:result.presentationLayout?.findingCount}));
}
