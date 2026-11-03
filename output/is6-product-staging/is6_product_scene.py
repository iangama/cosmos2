"""Product revision of the proven scene protocol; frozen prototype stays intact."""
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
sys.path.insert(0, str(ROOT / 'output/is6-spatial-bridge-staging'))
import is6_scene_transaction as protocol

artifact = protocol.base.artifact
lua = protocol.lua


class Owner(protocol.Owner):
    def __init__(self, native, phase):
        super().__init__(native, phase)
        self.retired = []
        self.faulted = False

    def commit(self, candidate, visible=True, cancel=None):
        protocol.check_cancel(cancel)
        if type(visible) is not bool or not isinstance(candidate, protocol.Candidate) or not candidate.attached:
            raise ValueError('Candidata oculta pronta obrigatória.')
        if self.faulted:
            raise ValueError('Restauração nativa pendente; feche a vista para recuperar.')
        state = candidate.read_native()
        if not state['exists'] or state['draw']:
            raise ValueError('A candidata deve permanecer oculta até a confirmação.')
        old = self.active
        context = self.context or self._capture()
        before = self.native('return {camera=openspace.navigation.getNavigationState("Root")}')['camera']
        rollback = 'openspace.navigation.setNavigationState(' + lua(before) + ');'
        rollback += 'if openspace.hasSceneGraphNode(' + lua(candidate.wire) + ') then openspace.setPropertyValueSingle("Scene.' + candidate.wire + '.Renderable.DrawElements",false) end;'
        if old:
            rollback += 'openspace.setPropertyValueSingle("Scene.' + old.wire + '.Renderable.DrawElements",' + lua(old.visible) + ');'
        else:
            rollback += 'for n,v in pairs(' + lua(context['flags']) + ') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;'
        code = 'local is6_product_commit=' + lua(candidate.wire) + ';'
        for name in [candidate.frame, candidate.wire, candidate.focus] + ([old.wire] if old else []):
            code += 'if not openspace.hasSceneGraphNode(' + lua(name) + ') then error("Spatial commit node unavailable") end;'
        apply = 'for n,v in pairs(' + lua(context['flags']) + ') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",false) end end;'
        if old:
            apply += 'openspace.setPropertyValueSingle("Scene.' + old.wire + '.Renderable.DrawElements",false);'
        apply += 'openspace.setPropertyValueSingle("Scene.' + candidate.wire + '.Renderable.DrawElements",' + lua(visible) + ');openspace.navigation.setNavigationState(' + lua(candidate.desired_camera()) + ');'
        code += 'local ok,err=pcall(function() ' + apply + ' end);if not ok then ' + rollback + ' error(tostring(err)) end;return {committed=true}'
        protocol.check_cancel(cancel)
        try:
            if self.native(code).get('committed') is not True:
                raise ValueError('Confirmação de troca da malha ausente.')
            # Readback belongs to the transaction, before publishing or retiring.
            confirmed = candidate.read_native()
            if not confirmed['exists'] or confirmed['draw'] is not visible or confirmed['center'] != state['center'] or confirmed['scale'] != state['scale'] or confirmed['file'] != state['file']:
                raise ValueError('A leitura nativa da candidata diverge.')
        except Exception:
            try:
                if self.native(rollback + 'return {restored=true}').get('restored') is not True:
                    raise ValueError('Confirmação de restauração ausente.')
            except Exception as error:
                self.context = context
                self.faulted = True
                self.error = 'Rollback da cena não confirmado: ' + str(error)
            raise
        candidate.visible = visible
        self.active, self.context, self.error = candidate, context, None
        if old:
            self.retired.append(old)
            try:
                old.close()
                self.retired.remove(old)
            except Exception as error:
                self.error = 'Vista confirmada; limpeza anterior pendente: ' + str(error)
        return confirmed

    def close(self):
        # Keep every owner until its native removal is acknowledged.
        if self.context:
            self.native('openspace.navigation.setNavigationState(' + lua(self.context['camera']) + ');return {restored=true}')
        for candidate in list(self.retired):
            candidate.close()
            self.retired.remove(candidate)
        if self.active:
            self.active.close()
            self.active = None
        if self.context:
            self.native('for n,v in pairs(' + lua(self.context['flags']) + ') do if openspace.hasSceneGraphNode(n) then openspace.setPropertyValueSingle("Scene."..n..".Renderable.Enabled",v) end end;return {restored=true}')
        self.context, self.error, self.faulted = None, None, False
