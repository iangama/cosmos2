'use strict';
let jupiterFieldReading = null;
const jupiterCoordinates = () => [Number($('jupiter-field-radius').value) * 71492000,
  Number($('jupiter-field-latitude').value), Number($('jupiter-field-longitude').value), Number($('jupiter-field-degree').value)];

function updateJupiterField(p, body) {
  const available = body?.reference_id === 'sol:naif:599';
  $('jupiter-field-sample').disabled = pending || !available;
  const reading = jupiterFieldReading;
  if (!available) {
    $('jupiter-field-reading').textContent = 'O JRM33 está associado a Júpiter. Selecione Júpiter para consultar este instrumento.';
    return;
  }
  if (!reading || reading.system_id !== p.system_id || reading.body_id !== body.id) {
    $('jupiter-field-reading').textContent = 'Escolha um ponto e meça o campo na época da cena.';
    return;
  }
  const stale = reading.edit_token !== p.edit_token || reading.revision !== p.revision || reading.time !== p.time;
  const c = reading.coordinates;
  const changed = jupiterCoordinates().some((v, i) => v !== [c.radius_m, c.latitude_planetocentric_deg, c.longitude_east_deg, reading.degree][i]);
  $('jupiter-field-reading').textContent =
    (stale ? 'Amostra fixa; a fase atual mudou.\n' : 'Fase atual confirmada.\n') +
    (changed ? 'Coordenadas ou grau alterados; os valores abaixo são da amostra anterior.\n' : '') +
    `Época da cena UTC: ${reading.epoch.utc}\n` +
    `Ponto: ${(c.radius_m / reading.reference_radius_m).toPrecision(6)} Rj · latitude ${c.latitude_planetocentric_deg}° · longitude leste ${c.longitude_east_deg}°\n` +
    `Grau ${reading.degree}${reading.degree === 18 ? ' · truncamento exploratório' : reading.degree === 1 ? ' · referência de dipolo' : ' · truncamento padrão'}\n` +
    `|B| = ${(reading.field_norm_T * 1e9).toPrecision(8)} nT\n` +
    `B em Sistema III x/y/z: ${solarVector(reading.field_SystemIII_T)} T\n` +
    `B em J2000 x/y/z: ${solarVector(reading.field_J2000_T)} T\n` +
    'Coeficientes estáticos da época 2019; sem variação secular aplicada.\n' +
    'Rotação Sistema III destrógiro → J2000 pelo PCK, com nutação/precessão.\n' +
    'Componente interna; sem correntes externas ou previsão do campo total.\n' +
    'Incerteza local não propagada; diferença entre graus não é barra de erro.';
}
window.updateJupiterField = updateJupiterField;

$('jupiter-field-form').onsubmit = async event => {
  event.preventDefault();
  if (pending || !$('jupiter-field-form').reportValidity()) return;
  const [radius_m, latitude_deg, east_longitude_deg, degree] = jupiterCoordinates();
  await command({command: 'pause'}, 'Evolução pausada para consultar o campo joviano.');
  const p = appState?.physics;
  if (!p?.paused) return;
  const result = await command({...editGuard(p), body_id: $('solar-body').value, radius_m, latitude_deg, east_longitude_deg, degree},
    'Campo joviano medido na fase confirmada.', '/api/solar/jupiter-field');
  if (result?.ack?.result) {
    jupiterFieldReading = result.ack.result;
    updateJupiterField(appState.physics, appState.physics.bodies.find(b => b.id === $('solar-body').value));
  }
};
for (const id of ['jupiter-field-radius', 'jupiter-field-latitude', 'jupiter-field-longitude', 'jupiter-field-degree']) $(id).oninput = () => {
  const p = appState?.physics;
  if (p) updateJupiterField(p, p.bodies.find(b => b.id === $('solar-body').value));
};
