'use strict';
(() => {
  const el = id => document.getElementById('catalog-' + id);
  const format = value => value.toLocaleString('pt-BR', {maximumSignificantDigits: 12});
  let snapshot = null;
  let pending = false;

  function card(label, value, origin, source, printed) {
    const section = document.createElement('section');
    section.className = 'property-card';
    const title = document.createElement('h3');
    title.textContent = label;
    const reading = document.createElement('div');
    reading.className = 'property-value';
    reading.textContent = value;
    const note = document.createElement('p');
    note.className = 'muted';
    note.textContent = origin;
    section.append(title, reading, note);
    if (source) {
      const link = document.createElement('a');
      link.href = source;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = source.endsWith('.bsp') ? 'Kernel original JPL (.bsp) ↗' : 'Fonte do parâmetro ↗';
      section.append(link);
    }
    if (printed) {
      const detail = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = 'Valor impresso na fonte';
      const printedValue = document.createElement('code');
      printedValue.textContent = printed;
      detail.append(summary, printedValue);
      section.append(detail);
    }
    return section;
  }

  function render() {
    const body = snapshot.bodies.find(item => item.naif_id === el('body').value);
    el('title').textContent = body.name + ' · ' + body.id;
    el('epoch').textContent = snapshot.epoch.utc + ' · ET/TDB ' +
      format(snapshot.epoch.et_tdb_s) + ' s desde J2000';
    const vector = (values, unit) => values.map((value, index) =>
      ['x', 'y', 'z'][index] + ' = ' + format(value) + ' ' + unit).join('\n');
    const provider = body.state_provider;
    el('properties').replaceChildren(
      card('Posição', vector(body.position_m, 'm'), provider.model + ' · cadeia ' +
        provider.chain_naif_ids.join(' → ')),
      card('Velocidade', vector(body.velocity_m_s, 'm/s'), 'Derivada do estado geométrico em J2000/ICRF.'),
      card('Parâmetro gravitacional GM', format(body.GM.value) + ' m³/s²',
        'Parâmetro do corpo físico. Incerteza da fonte desconhecida.', body.GM.source,
        body.GM.raw_value_km3_s2 + ' km³/s²'),
      card('Semieixos de referência', body.shape.radii_m.map(value => format(value) + ' m').join(' · '),
        'Semieixos de referência do PCK00011.'),
      card('Orientação', body.rotation.frame || 'Orientação ainda sem cadastro',
        body.rotation.frame ? 'Rotação IAU geral do PCK00011.' : 'Consulte a definição da referência selecionada.')
    );
    el('generation').textContent = 'SHA256 dos dados ' + snapshot.provenance.data_sha256;
  }

  async function query(event) {
    if (event) event.preventDefault();
    if (pending || !el('form').reportValidity()) return;
    pending = true;
    el('query').disabled = true;
    el('export').disabled = true;
    el('status').textContent = 'Consultando referência…';
    try {
      const value = el('utc').value;
      const utc = value.length === 16 ? value + ':00' : value;
      const response = await fetch('/api/planet-reference?utc=' + encodeURIComponent(utc));
      const data = await response.json();
      if (!response.ok) throw Error(data.error || 'Consulta indisponível.');
      snapshot = data;
      const selected = el('body').value || '399';
      el('body').replaceChildren(...data.bodies.map(body => new Option(body.name + ' · NAIF' + body.naif_id, body.naif_id)));
      el('body').value = selected;
      el('body').disabled = false;
      render();
      el('status').textContent = 'Sol, oito planetas e Lua na época consultada.';
    } catch (error) {
      el('status').textContent = error.message;
    } finally {
      pending = false;
      el('query').disabled = false;
      el('export').disabled = !snapshot;
    }
  }

  el('form').onsubmit = query;
  el('body').onchange = render;
  el('export').onclick = async () => {
    if (pending || !snapshot) return;
    pending = true;
    el('export').disabled = true;
    try {
      const response = await fetch('/api/planet-reference/export', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({utc: snapshot.epoch.utc})
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw Error(data.error || 'Exportação indisponível.');
      el('export-path').textContent = data.export_file;
      el('status').textContent = 'Estado consultado e fontes exportados.';
    } catch (error) {
      el('status').textContent = error.message;
    } finally {
      pending = false;
      el('export').disabled = false;
    }
  };
  query();
})();
