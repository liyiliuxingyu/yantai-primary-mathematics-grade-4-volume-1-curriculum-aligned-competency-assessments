import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const W=path.resolve('p74_review/ppt_recheck/v1_2/v2');
const source=path.resolve('p74_review/bundle/讲解课件/小学四上同步素养卷第2册讲解课件答案.pptx');
const name=path.basename(source),SK='/root/.codex/skills/builtins/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(path.join(W,'final'),{recursive:true});
await fs.mkdir(path.join(W,'qa'),{recursive:true});
const sourceSHA=crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex');
const result=await finalizePresentation({
 workspaceDir:W,candidatePath:path.join(W,'draft2',name),finalPath:path.join(W,'final',name),
 pythonExecutable:process.env.CODEX_PRIMARY_RUNTIME_PYTHON,
 integrityValidatorPath:SK+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:SK+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:479,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'reference',families:['Droid Sans Fallback'],referencePath:source,referenceSha256:sourceSHA},
 verifyArtifactToolImport:true,receiptPath:path.join(W,'qa/volume2.validation.json')
});
console.log(JSON.stringify(result));
