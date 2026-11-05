"""Product revision of the proven scene protocol; frozen prototype stays intact."""
from pathlib import Path
import sys
import time

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
sys.path.insert(0, str(ROOT / 'output/is6-spatial-bridge-staging'))
import is6_scene_transaction as protocol

artifact = protocol.base.artifact
lua = protocol.lua


class Candidate(protocol.Candidate):
    def __init__(self, native, run, folder):
        super().__init__(native, run, folder)
        count = self.payload['configuration']['radial_count']
        self.presentation = dict(opacity=min(.65, .65*65/count), line_width=1.)

    def attach(self, cancel=None):
        began = time.monotonic()
        try:
            super().attach(cancel)
            protocol.check_cancel(cancel)
            self.native('openspace.setPropertyValueSingle("Scene.' + self.wire + '.Renderable.Opacity",' + lua(self.presentation['opacity']) + ');openspace.setPropertyValueSingle("Scene.' + self.wire + '.Renderable.LineWidth",1);return {styled=true}')
            protocol.check_cancel(cancel)
            state = self.read_native()
            if abs(state['opacity']-self.presentation['opacity']) > 1e-6 or state['line_width'] != 1.:
                raise ValueError('Estilo da malha oculta não confirmado.')
            self.ready_s = time.monotonic()-began
            if self.ready_s > 15:
                raise TimeoutError('Preparação da malha excedeu15s.')
            return state
        except Exception:
            self.close()
            raise

    def read_native(self):
        result = super().read_native()
        result.update(self.native('return {opacity=openspace.propertyValue("Scene.' + self.wire + '.Renderable.Opacity"),line_width=openspace.propertyValue("Scene.' + self.wire + '.Renderable.LineWidth")}'))
        return result

    def desired_camera(self):
        unit = self.prepared['normalization_unit_m']
        extent = max(1., self.prepared['plot_radius_normalized'])
        u, v, n = self.payload['configuration']['orientation']
        return dict(Anchor=self.focus, ReferenceFrame='Root',
                    Position=[(-2.6*v[k]+1.7*n[k])*extent*unit for k in range(3)], Up=list(n))


class Owner(protocol.Owner):
    def __init__(self, native, phase):
        super().__init__(native, phase)
        self.retired = []
        self.faulted = False

    def prepare(self, run, folder, cancel=None):
        protocol.check_cancel(cancel)
        candidate = Candidate(self.native, run, folder)
        try:
            candidate.attach(cancel)
            return candidate
        except Exception:
            candidate.close()
            raise

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
