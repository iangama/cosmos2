"""Isolate a pending-node lifetime correction; preserve all measured runtimes and science."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'.upstream/openspace'
DEST=ROOT/'output/node-lifecycle-staging'
NAMES=['include/openspace/scene/sceneinitializer.h','src/scene/sceneinitializer.cpp',
       'src/scene/scene.cpp','src/scene/scene_lua.inl','src/scene/scenegraphnode.cpp',
       'src/engine/openspaceengine_lua.inl','src/engine/openspaceengine.cpp']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if DEST.exists():raise FileExistsError('Preserve prior lifecycle preparation.')
    DEST.mkdir()
    preserved={name:sha(ROOT/name) for name in ['.runtime-cloud/bin/OpenSpace.exe','.runtime-topic-cleanup/bin/OpenSpace.exe',
        'evidence/built-runtime-cloud.json','evidence/built-runtime-topic-cleanup.json','user/sessions/latest.json']}
    before={name:sha(UP/name) for name in NAMES}
    (DEST/'original-source-sha256.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(DEST/'before-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in NAMES:
            p=DEST/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(UP/name,p);archive.write(p,name)
    def replace(name,old,new,count=1):
        p=UP/name;text=p.read_text(encoding='utf-8');assert text.count(old)==count,(name,old,text.count(old))
        p.write_text(text.replace(old,new),encoding='utf-8')
    replace(NAMES[0],'    void initializeNode(SceneGraphNode* node);',
        '    void initializeNode(SceneGraphNode* node);\n    // Join this node\'s CPU work and erase its pending GL reference before deletion.\n    void cancelInitialization(SceneGraphNode* node);')
    replace(NAMES[1],'#include <chrono>','#include <algorithm>\n#include <chrono>')
    replace(NAMES[1],'std::vector<SceneGraphNode*> SceneInitializer::takeInitializedNodes() {',
        '''void SceneInitializer::cancelInitialization(SceneGraphNode* node) {
    // The worker holds _mutex through its final LoadingScreen access, so once
    // the node leaves this set and we acquire the lock it is safe to destroy.
    for (;;) {
        {
            const std::unique_lock lock(_mutex);
            if (!_initializingNodes.contains(node)) {
                std::erase(_initializedNodes, node);
                return;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}

std::vector<SceneGraphNode*> SceneInitializer::takeInitializedNodes() {''')
    replace(NAMES[2],'    return _rootNode.detachChild(node);',
        '    _initializer->cancelInitialization(&node);\n    ghoul_assert(node.parent(), "Cannot detach the root node");\n    return node.parent()->detachChild(node);')
    replace(NAMES[3],'''        ghoul::mm_unique_ptr<SceneGraphNode> n = localNode->parent()->detachChild(
            *localNode
        );''',
        '''        ghoul::mm_unique_ptr<SceneGraphNode> n =
            global::renderEngine->scene()->detachNode(*localNode);''',count=2)
    replace(NAMES[4],'void SceneGraphNode::deinitializeGL() {\n    ZoneScoped;',
        '''void SceneGraphNode::deinitializeGL() {
    // A cancelled CPU initializer may never have allocated any GL resources.
    if (_state.load() != State::GLInitialized) {
        return;
    }
    ZoneScoped;''')
    replace(NAMES[5],'/** Starts a bounded capture of actual SGCT frame intervals, including VSync. */',
        '''/** CPU initialization status for bounded scene-readiness checks in this candidate. */
[[codegen::luawrap]] ghoul::Dictionary cosmos2SceneInitialization() {
    ghoul::Dictionary result;
    result.setValue("cpu_initializing", global::renderEngine->scene()->isInitializing());
    result.setValue("policy", std::string("CPU work only; observe later rendered frames for GL readiness"));
    return result;
}

/** Starts a bounded capture of actual SGCT frame intervals, including VSync. */''')
    replace(NAMES[6],'            codegen::lua::Cosmos2MemoryMetrics,',
        '            codegen::lua::Cosmos2MemoryMetrics,\n            codegen::lua::Cosmos2SceneInitialization,')
    patch=''
    for name in NAMES:
        patch+=''.join(difflib.unified_diff((DEST/'before'/name).read_text(encoding='utf-8').splitlines(True),
            (UP/name).read_text(encoding='utf-8').splitlines(True),fromfile='before/'+name,tofile='node-lifecycle/'+name))
    (DEST/'node-lifecycle.patch').write_text(patch,encoding='utf-8')
    assert all(sha(ROOT/name)==value for name,value in preserved.items())
    report={'schema':1,'prepared':True,'accepted':False,'before_sha256':before,
        'changed_sha256':{name:sha(UP/name) for name in NAMES},'preserved_sha256':preserved,
        'scope':'Cancel/wait CPU initialization and remove pending GL references before node destruction; skip GL deinit when never initialized. Separate unapproved runtime, no field/solver/renderer appearance changes. Native stress/replay/profile pending.'}
    (DEST/'preparation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'prepared':True,'changed_files':len(NAMES),'measured_runtimes_preserved':True}))


if __name__=='__main__':main()
