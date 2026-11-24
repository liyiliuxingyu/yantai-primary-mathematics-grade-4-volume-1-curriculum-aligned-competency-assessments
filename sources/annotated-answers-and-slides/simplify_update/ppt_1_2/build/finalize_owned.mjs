import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const B=path.resolve('simplify_review/ppt_1_2');
const SK='/root/.codex/skills/builtins/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(path.join(B,'final'),{recursive:true});
await fs.mkdir(path.join(B,'qa_receipts'),{recursive:true});
for(const v of [1,2]){
 const n=`小学四上同步素养卷第${v}册讲解课件答案.pptx`;
 const r=await finalizePresentation({workspaceDir:B,candidatePath:path.join(B,'draft2',n),finalPath:path.join(B,'final',n),pythonExecutable:process.env.CODEX_PRIMARY_RUNTIME_PYTHON,integrityValidatorPath:path.join(SK,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SK,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000'],explicitTotalSlideCount:v===1?426:479,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],verifyArtifactToolImport:true,receiptPath:path.join(B,'qa_receipts',`volume${v}.validation.json`)});
 console.log(JSON.stringify({volume:v,final:r.finalPath,receipt:r.receiptPath}));
}
