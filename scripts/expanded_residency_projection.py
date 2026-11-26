"""Keep every raw API response; transitional envelopes need not be scientific phases."""
import expanded_residency_contract_v2 as c


def project(inputs, kind):
    try:
        value = c.scenario(inputs['state'], inputs['modules'], inputs['navigation'])
    except (KeyError, TypeError, ValueError) as error:
        c.require(kind in ['prepare', 'transition', 'cleanup'], 'Incomplete scientific scenario outside a transition')
        return dict(scenario=None, scenario_projection_error=dict(type=type(error).__name__, message=str(error)))
    return dict(scenario=value, scenario_projection_error=None)
