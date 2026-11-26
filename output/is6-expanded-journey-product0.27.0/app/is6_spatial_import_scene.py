"""Archive science and current live camera/flags have separate ownership."""
import copy
from is6_product_scene import Owner as BaseOwner


class Owner(BaseOwner):
    def __init__(self, native, display_phase):
        # BaseOwner captures nodes from current_phase. These must be the live
        # copy's identities, even when a candidate contains an archived phase.
        super().__init__(native, display_phase)
        self.display_phase = copy.deepcopy(display_phase)
        self.scientific_phase = None

    def commit(self, candidate, visible=True, cancel=None):
        scientific_phase = copy.deepcopy(candidate.payload['phase'])
        answer = super().commit(candidate, visible=visible, cancel=cancel)
        self.scientific_phase = scientific_phase
        return answer
