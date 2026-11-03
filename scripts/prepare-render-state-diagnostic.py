"""Prepare bounded, opt-in GL observations in a separate unapproved runtime build."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'.upstream/openspace'
DEST=ROOT/'output/render-state-diagnostic-staging'
NAMES=['src/engine/openspaceengine_lua.inl','src/engine/openspaceengine.cpp',
    'src/rendering/framebufferrenderer.cpp','modules/cefwebgui/src/guirenderhandler.cpp']


def main():
    if DEST.exists():raise FileExistsError('Preserve previous preparation.')
    DEST.mkdir()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    preserved={p:sha(ROOT/p) for p in ['.runtime-cloud/bin/OpenSpace.exe','.runtime-topic-cleanup/bin/OpenSpace.exe',
        'evidence/built-runtime-cloud.json','evidence/built-runtime-topic-cleanup.json','user/sessions/latest.json']}
    originals={name:sha(UP/name) for name in NAMES}
    with zipfile.ZipFile(DEST/'before-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in NAMES:
            target=DEST/'before'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(UP/name,target)
            archive.write(UP/name,name)
    header=UP/'include/openspace/rendering/cosmos2gldiagnostic.h'
    if header.exists():raise FileExistsError(header)
    header.write_text(r'''// Cosmos2 local diagnostic only: bounded snapshots, inactive by default.
#pragma once
#include <ghoul/opengl/ghoul_gl.h>
#include <array>
#include <cstddef>

namespace openspace::cosmos2gl {
struct Sample {
    const char* phase = "";
    unsigned long long frame = 0;
    GLboolean depthTest = false, depthWrite = false, scissor = false, stencil = false;
    GLboolean cull = false;
    std::array<GLboolean,4> colorWrite = {};
    GLint depthFunction = 0, drawFBO = 0, readFBO = 0, packBuffer = 0;
    std::array<GLint,4> viewport = {}, scissorBox = {};
    std::array<GLdouble,2> depthRange = {};
    GLdouble clearDepth = 0;
    GLfloat depthCenter = -1;
};
inline bool active = false;
inline unsigned long long frame = 0;
inline std::size_t count = 0;
inline constexpr std::size_t Capacity = 128;
inline std::array<Sample,Capacity> samples = {};

inline void record(const char* phase, bool readDepth = false) {
    if (!active) { return; }
    if (count >= Capacity) { active = false; return; }
    Sample& s = samples[count++];
    s = Sample(); s.phase = phase; s.frame = frame;
    s.depthTest = glIsEnabled(GL_DEPTH_TEST);
    glGetBooleanv(GL_DEPTH_WRITEMASK, &s.depthWrite);
    glGetIntegerv(GL_DEPTH_FUNC, &s.depthFunction);
    glGetDoublev(GL_DEPTH_CLEAR_VALUE, &s.clearDepth);
    glGetDoublev(GL_DEPTH_RANGE, s.depthRange.data());
    s.scissor = glIsEnabled(GL_SCISSOR_TEST);
    glGetIntegerv(GL_SCISSOR_BOX, s.scissorBox.data());
    s.stencil = glIsEnabled(GL_STENCIL_TEST);
    s.cull = glIsEnabled(GL_CULL_FACE);
    glGetBooleanv(GL_COLOR_WRITEMASK, s.colorWrite.data());
    glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &s.drawFBO);
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &s.readFBO);
    glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING, &s.packBuffer);
    glGetIntegerv(GL_VIEWPORT, s.viewport.data());
    GLint packSkipRows = 0, packSkipPixels = 0;
    GLboolean packSwapBytes = false;
    glGetIntegerv(GL_PACK_SKIP_ROWS, &packSkipRows);
    glGetIntegerv(GL_PACK_SKIP_PIXELS, &packSkipPixels);
    glGetBooleanv(GL_PACK_SWAP_BYTES, &packSwapBytes);
    if (readDepth && s.packBuffer == 0 && packSkipRows == 0 &&
        packSkipPixels == 0 && packSwapBytes == GL_FALSE)
    {
        glReadPixels(s.viewport[0]+s.viewport[2]/2, s.viewport[1]+s.viewport[3]/2,
            1, 1, GL_DEPTH_COMPONENT, GL_FLOAT, &s.depthCenter);
    }
    if (count >= Capacity) { active = false; }
}
} // namespace openspace::cosmos2gl
''',encoding='utf-8')
    p=UP/NAMES[0];s=p.read_text()
    s=s.replace('#include <openspace/openspace.h>','#include <openspace/openspace.h>\n#include <openspace/rendering/cosmos2gldiagnostic.h>',1)
    marker='/** Starts a bounded capture of actual SGCT frame intervals, including VSync. */'
    api=r'''/** Opt-in GL readback diagnostics; no render-state setters or science changes. */
[[codegen::luawrap]] ghoul::Dictionary cosmos2GLDiagnostic(bool enabled = false,
                                                         bool clear = false)
{
    if (clear) { cosmos2gl::count = 0; cosmos2gl::frame = 0; }
    cosmos2gl::active = enabled;
    ghoul::Dictionary rows;
    for (std::size_t i = 0; i < cosmos2gl::count; ++i) {
        const cosmos2gl::Sample& s = cosmos2gl::samples[i];
        ghoul::Dictionary d;
        d.setValue("phase", std::string(s.phase));
        d.setValue("frame", static_cast<double>(s.frame));
        d.setValue("depth_test", s.depthTest != GL_FALSE);
        d.setValue("depth_write", s.depthWrite != GL_FALSE);
        d.setValue("depth_function", static_cast<double>(s.depthFunction));
        d.setValue("clear_depth", s.clearDepth);
        d.setValue("depth_center", static_cast<double>(s.depthCenter));
        d.setValue("depth_range", glm::dvec2(s.depthRange[0],s.depthRange[1]));
        d.setValue("scissor", s.scissor != GL_FALSE);
        d.setValue("scissor_box", glm::ivec4(s.scissorBox[0],s.scissorBox[1],s.scissorBox[2],s.scissorBox[3]));
        d.setValue("stencil", s.stencil != GL_FALSE);
        d.setValue("cull", s.cull != GL_FALSE);
        d.setValue("color_write", glm::ivec4(s.colorWrite[0],s.colorWrite[1],s.colorWrite[2],s.colorWrite[3]));
        d.setValue("draw_FBO", static_cast<double>(s.drawFBO));
        d.setValue("read_FBO", static_cast<double>(s.readFBO));
        d.setValue("pixel_pack_buffer", static_cast<double>(s.packBuffer));
        d.setValue("viewport", glm::ivec4(s.viewport[0],s.viewport[1],s.viewport[2],s.viewport[3]));
        rows.setValue(std::to_string(i+1), d);
    }
    ghoul::Dictionary result;
    result.setValue("samples", rows);
    result.setValue("active", cosmos2gl::active);
    result.setValue("capacity", static_cast<double>(cosmos2gl::Capacity));
    result.setValue("count", static_cast<double>(cosmos2gl::count));
    return result;
}

'''
    assert s.count(marker)==1;s=s.replace(marker,api+marker,1);p.write_text(s)
    p=UP/NAMES[1];s=p.read_text();marker='            codegen::lua::Cosmos2MemoryMetrics,'
    assert s.count(marker)==1;s=s.replace(marker,marker+'\n            codegen::lua::Cosmos2GLDiagnostic,',1);p.write_text(s)
    p=UP/NAMES[2];s=p.read_text();s=s.replace('#include <openspace/rendering/volumeraycaster.h>',
        '#include <openspace/rendering/volumeraycaster.h>\n#include <openspace/rendering/cosmos2gldiagnostic.h>',1)
    marker='    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);'
    # Instrument only the main G-buffer clear, not unrelated auxiliary targets.
    start=s.index('void FramebufferRenderer::render(Scene* scene, Camera* camera')
    prefix,tail=s[:start],s[start:]
    assert marker in tail
    tail=tail.replace(marker,'    if (cosmos2gl::active) { ++cosmos2gl::frame; }\n    cosmos2gl::record("before_clear", true);\n'+marker+'\n    cosmos2gl::record("after_clear", true);',1)
    marker='        data.renderBinMask = static_cast<int>(Renderable::RenderBin::Opaque);\n        scene->render(data, tasks);'
    assert marker in tail;tail=tail.replace(marker,marker+'\n        cosmos2gl::record("after_opaque", true);',1)
    marker='        TracyGpuZone("Raycaster Tasks")'
    assert marker in tail;tail=tail.replace(marker,'        cosmos2gl::record("after_pre_deferred", true);\n'+marker,1)
    p.write_text(prefix+tail)
    p=UP/NAMES[3];s=p.read_text();marker='#include <modules/cefwebgui/include/guirenderhandler.h>'
    s=s.replace(marker,marker+'\n#include <openspace/rendering/cosmos2gldiagnostic.h>',1)
    marker='    updateTexture();';assert s.count(marker)==1;s=s.replace(marker,'    cosmos2gl::record("before_CEF");\n'+marker,1)
    marker='    glEnable(GL_CULL_FACE);';assert s.count(marker)==1;s=s.replace(marker,marker+'\n    cosmos2gl::record("after_CEF");',1);p.write_text(s)
    report={'schema':1,'prepared':True,'before_sha256':originals,'changed_sha256':{name:sha(UP/name) for name in NAMES},
        'new_header':header.relative_to(UP).as_posix(),'new_header_sha256':sha(header),'preserved_sha256':preserved,
        'scope':'Read-only GL observations, opt-in and bounded to128 samples; no setters, force/integrator/model changes or promotion. Stalls while enabled are diagnostic overhead, not performance evidence.'}
    (DEST/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'prepared':True,'changed_files':len(NAMES),'new_header':report['new_header']}))


if __name__=='__main__':main()
