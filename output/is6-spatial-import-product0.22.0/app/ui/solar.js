'use strict';
let solarReading = null;
let solarIdentity = null;
const solarVector = values => values.map(x => x.toExponential(5)).join(' / ');

function updateSolar(p) {
  const initial = p.atlas_initial;
  const available = initial?.kind === 'solar_four_physical_centers';
  $('solar-panel').hidden = !available;
  if (!available) {solarReading = null; solarIdentity = null; return;}
  if (solarIdentity !== p.system_id || $('solar-body').options.length !== p.bodies.length) {
    const selected = $('solar-body').value;
    $('solar-body').replaceChildren();
    for (const body of p.bodies) {
      const option = document.createElement('option');
      option.value = body.id; option.textContent = body.name; $('solar-body').append(option);
    }
    $('solar-body').value = p.bodies.some(b => b.id === selected) ? selected : (p.bodies.find(b => b.reference_id === 'sol:naif:399') || p.bodies[0]).id;
    solarIdentity = p.system_id;
  }
  const body = p.bodies.find(b => b.id === $('solar-body').value);
  if (window.updateSolarTide) updateSolarTide(p, body);
  if (window.updateEarthField) updateEarthField(p, body);
  if (window.updateJupiterField) updateJupiterField(p, body);
  if (window.updateBodyFieldVector) updateBodyFieldVector(p, body);
  const reference = initial.reference_catalog.bodies.find(b => b.id === body?.reference_id);
  $('solar-capabilities').textContent = reference ?
    `${reference.name} · ${reference.id}\nGravidade: evolução newtoniana com as fontes ativas.\nEM: ${body.reference_id === 'sol:naif:399' ? 'Consulta IGRF14 na época da cena; campo interno em um ponto, sem força sobre o centro neutro.' : body.reference_id === 'sol:naif:599' ? 'Consulta JRM33 ligada à cena, coeficientes estáticos de 2019; componente interna sem força sobre o centro neutro.' : reference.capabilities.magnetism.reason}\nForte/fraca: bancadas disponíveis; sem composição ou processo acoplado ao corpo.` :
    'Corpo de modelo criado nesta sessão. Gravidade com as fontes ativas; outras camadas não associadas.';
  $('solar-sample').disabled = pending || !body;
  $('solar-view-body').disabled = pending || !body;
  $('solar-source-readings').replaceChildren();
  if (!solarReading || solarReading.system_id !== p.system_id || solarReading.body_id !== body?.id) {
    $('solar-reading').textContent = 'Escolha um corpo e calcule as contribuições.'; return;
  }
  const stale = solarReading.edit_token !== p.edit_token || solarReading.revision !== p.revision || solarReading.time !== p.time;
  $('solar-reading').textContent = (stale ? 'Amostra fixa; a fase atual mudou.\n' : 'Fase atual confirmada.\n') +
    `t = ${(solarReading.time * p.physical_scale.time_unit_s / 3600).toPrecision(7)} h · revisão ${solarReading.revision}\n` +
    `g total x/y/z: ${solarVector(solarReading.acceleration_m_s2)} m/s²\n|g total| = ${solarReading.acceleration_norm_m_s2.toExponential(6)} m/s²`;
  for (const source of solarReading.sources) {
    const row = document.createElement('p'); row.className = 'field-help'; row.dataset.solarSource = source.id;
    row.textContent = `${source.name} · ${source.reference_id || 'modelo do usuário'}\ng x/y/z: ${solarVector(source.acceleration_m_s2)} m/s²\n|g| = ${Math.hypot(...source.acceleration_m_s2).toExponential(6)} m/s²`;
    $('solar-source-readings').append(row);
  }
}
window.updateSolar = updateSolar;
$('solar-body').onchange = () => {if (appState?.physics) updateSolar(appState.physics);};
$('solar-view-body').onclick = () => {
  $('edit-body').value = $('solar-body').value;
  $('view-edit-body').click();
};
$('solar-sample').onclick = async () => {
  if (pending) return;
  await command({command: 'pause'}, 'Evolução pausada para medir o campo.');
  const p = appState?.physics;
  if (!p?.paused) return;
  const response = await command({...editGuard(p), command: 'solar_reading', body_id: $('solar-body').value}, 'Contribuições medidas na fase confirmada.');
  if (response?.ack?.result) {solarReading = response.ack.result; updateSolar(appState.physics);}
};
