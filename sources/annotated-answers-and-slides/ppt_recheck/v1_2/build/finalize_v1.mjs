import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import crypto from 'node:crypto';
const [workArg,candidateArg,referenceArg]=process.argv.slice(2);
const work=path.resolve(workArg),candidate=path.resolve(candidateArg),referencePath=path.resolve(referenceArg);
const skill='/root/.codex/skills/builtins/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
await fs.mkdir(path.join(work,'qa'),{recursive:true});
await fs.mkdir(path.join(work,'validated'),{recursive:true});
const result=await finalizePresentation({
 workspaceDir:work,candidatePath:candidate,
 finalPath:path.join(work,'validated',path.basename(candidate)),
 pythonExecutable:process.env.CODEX_PRIMARY_RUNTIME_PYTHON,
 integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:426,
 requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'reference',families:['Droid Sans Fallback'],referencePath,referenceSha256:sha(await fs.readFile(referencePath))},
 verifyArtifactToolImport:true,
 receiptPath:path.join(work,'qa','finalizer_v1.json')
});
console.log(JSON.stringify(result));
