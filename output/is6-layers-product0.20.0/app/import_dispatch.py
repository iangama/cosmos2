"""Explicit parser dispatch: preserve the legacy atlas_sun_earth_moon format."""
from atlas_import import digest, generation


def validate(value):
    if isinstance(value, dict) and value.get('kind') == 'solar_four_physical_centers':
        from solar_import import validate as solar_validate
        return solar_validate(value)
    from atlas_import import validate as legacy_validate
    return legacy_validate(value)
