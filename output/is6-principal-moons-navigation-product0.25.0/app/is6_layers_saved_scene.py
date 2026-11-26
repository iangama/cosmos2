"""Keep archived science while owning flags/camera of the current live copy."""
import copy
from is6_layers_scene import Owner as BaseOwner, Pair, lua


class Owner(BaseOwner):
    def __init__(self,native,phase,*,display_phase=None):
        super().__init__(native,phase)
        self.display_phase=copy.deepcopy(phase if display_phase is None else display_phase)

    def context_now(self):
        names=['LabGrid','LabBarycenter','LabProbe']
        for body in self.display_phase['bodies']:
            names.extend(body[k] for k in ['scene_node','label_node','shape_node','spin_node'] if body.get(k))
        return self.native('local f={};for _,n in ipairs('+lua(names)+') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')

    def prepare(self,run,reading,folder):
        if self.faulted:raise ValueError('Native recovery required')
        # Pair.compose revalidates both models against the archived source phase.
        # Context ownership deliberately uses display_phase, whose live IDs may
        # differ after restarting the host or creating another solar copy.
        pair=Pair(self.native,run,reading,folder);self.prepared.append(pair)
        try:pair.attach()
        except Exception:
            pair.close();self.prepared.remove(pair);raise
        return pair

    def commit(self,pair,visible):
        answer=super().commit(pair,visible)
        self.phase=copy.deepcopy(pair.spatial.payload['phase'])
        return answer
