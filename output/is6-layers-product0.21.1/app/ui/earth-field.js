'use strict';
let earthFieldReading = null;
const earthCoordinates = () => [Number($('earth-field-latitude').value), Number($('earth-field-longitude').value), Number($('earth-field-altitude').value) * 1000];

function updateEarthField(p, body) {
  const available = body?.reference_id === 'sol:naif:399';
  $('earth-field-sample').disabled = pending || !available;
  const reading = earthFieldReading;
  if (!available) {
    $('earth-field-reading').textContent = 'O IGRF14 está associado à Terra. Selecione a Terra para consultar este instrumento.';
    return;
  }
  if (!reading || reading.system_id !== p.system_id || reading.body_id !== body.id) {
    $('earth-field-reading').textContent = 'Escolha um ponto e meça o campo na época da cena.';
    return;
  }
  const stale = reading.edit_token !== p.edit_token || reading.revision !== p.revision || reading.time !== p.time;
  const c = reading.coordinates;
  const changed = earthCoordinates().some((v, i) => v !== [c.latitude_deg, c.longitude_deg, c.altitude_m][i]);
  $('earth-field-reading').textContent =
    (stale ? 'Amostra fixa; a fase atual mudou.\n' : 'Fase atual confirmada.\n') +
    (changed ? 'Coordenadas alteradas; os valores abaixo são da amostra anterior.\n' : '') +
    `Época UTC: ${reading.epoch.utc}\nAno decimal: ${reading.epoch.decimal_UTC_year.toFixed(8)}\n` +
    `Ponto da amostra: ${c.latitude_deg}° / ${c.longitude_deg}° · ${(c.altitude_m / 1000).toPrecision(6)} km\n` +
    `|B| = ${(reading.field_norm_T * 1e9).toPrecision(8)} nT\n` +
    `Norte / leste / baixo: ${reading.field_NED_nT.map(v => v.toFixed(4)).join(' / ')} nT\n` +
    `B em J2000 x/y/z: ${solarVector(reading.field_J2000_T)} T\n` +
    (reading.epoch.decimal_UTC_year >= 2025 ? 'IGRF2025 + variação secular prevista até 2030.\n' : 'Interpolação das épocas IGRF14.\n') +
    (reading.orientation.status === 'prediction' ? 'Rotação terrestre: trecho previsto pelo provedor EOP.\n' : 'Rotação terrestre: trecho apoiado pelos dados EOP.\n') +
    `Último datum EOP: ${reading.orientation.last_datum_utc}\n` +
    'Incertezas locais do campo e da orientação não propagadas; não são zero.';
}
window.updateEarthField = updateEarthField;

$('earth-field-form').onsubmit = async event => {
  event.preventDefault();
  if (pending || !$('earth-field-form').reportValidity()) return;
  const [latitude_deg, longitude_deg, altitude_m] = earthCoordinates();
  await command({command: 'pause'}, 'Evolução pausada para consultar o campo terrestre.');
  const p = appState?.physics;
  if (!p?.paused) return;
  const result = await command({...editGuard(p), body_id: $('solar-body').value, latitude_deg, longitude_deg, altitude_m},
    'Campo terrestre medido na fase confirmada.', '/api/solar/earth-field');
  if (result?.ack?.result) {
    earthFieldReading = result.ack.result;
    updateEarthField(appState.physics, appState.physics.bodies.find(b => b.id === $('solar-body').value));
  }
};
for (const id of ['earth-field-latitude', 'earth-field-longitude', 'earth-field-altitude']) $(id).oninput = () => {
  const p = appState?.physics;
  if (p) updateEarthField(p, p.bodies.find(b => b.id === $('solar-body').value));
};
