'use strict';
let solarTideReading = null;
const tideOffset = () => [0, 1, 2].map(k => Number($('solar-tide-offset-' + k).value));

function updateSolarTide(p, body) {
  $('solar-tide-sample').disabled = pending || !body;
  $('solar-tide-sources').replaceChildren();
  const reading = solarTideReading;
  if (!reading || reading.system_id !== p.system_id || reading.body_id !== body?.id) {
    $('solar-tide-reading').textContent = 'Escolha o deslocamento e calcule a diferença do campo.';
    return;
  }
  const stale = reading.edit_token !== p.edit_token || reading.revision !== p.revision || reading.time !== p.time;
  const changedOffset = tideOffset().some((v, i) => v !== reading.offset_m[i]);
  $('solar-tide-reading').textContent =
    (stale ? 'Amostra fixa; a fase atual mudou.\n' : 'Fase atual confirmada.\n') +
    (changedOffset ? 'Deslocamento alterado; os valores abaixo são da amostra anterior.\n' : '') +
    `t = ${(reading.time * p.physical_scale.time_unit_s / 3600).toPrecision(7)} h · revisão ${reading.revision}\n` +
    `Deslocamento da amostra: ${solarVector(reading.offset_m)} m\n` +
    `Δg exato x/y/z: ${solarVector(reading.exact_m_s2)} m/s²\n` +
    `|Δg exato| = ${Math.hypot(...reading.exact_m_s2).toExponential(6)} m/s²\n` +
    `Δg linear x/y/z: ${solarVector(reading.linear_m_s2)} m/s²`;
  for (const source of reading.sources) {
    const row = document.createElement('p');
    row.className = 'field-help'; row.dataset.solarTideSource = source.id;
    row.textContent = `${source.name} · ${source.reference_id || 'modelo do usuário'}\n` +
      `Δg exato: ${solarVector(source.exact_m_s2)} m/s²\n` +
      `|Δg exato| = ${Math.hypot(...source.exact_m_s2).toExponential(6)} m/s²\n` +
      `Exato − linear: ${solarVector(source.nonlinear_residual_m_s2)} m/s²`;
    $('solar-tide-sources').append(row);
  }
}
window.updateSolarTide = updateSolarTide;

$('solar-tide-form').onsubmit = async event => {
  event.preventDefault();
  if (pending || !$('solar-tide-form').reportValidity()) return;
  const offset = tideOffset();
  await command({command: 'pause'}, 'Evolução pausada para medir a maré externa.');
  const p = appState?.physics;
  if (!p?.paused) return;
  const response = await command({...editGuard(p), body_id: $('solar-body').value, offset_m: offset},
    'Maré externa medida na fase confirmada.', '/api/solar/tide');
  if (response?.ack?.result) {
    solarTideReading = response.ack.result;
    updateSolarTide(appState.physics, appState.physics.bodies.find(b => b.id === $('solar-body').value));
  }
};
for (let i = 0; i < 3; i++) $('solar-tide-offset-' + i).oninput = () => {
  const p = appState?.physics;
  if (p) updateSolarTide(p, p.bodies.find(b => b.id === $('solar-body').value));
};
