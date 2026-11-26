/* Single-choice controls rendered inside the page: no native CEF popup surface. */
(() => {
  'use strict';
  const savedScale = localStorage.getItem('cosmos2-ui-scale');
  if (!document.getElementById('ui-scale') && ['1','1.25','1.5'].includes(savedScale)) {
    document.documentElement.style.setProperty('--science-ui-scale', savedScale);
    document.body.classList.toggle('science-large', Number(savedScale) > 1);
  }
  const controls = new Map();
  let serial = 0, opened = null, search = '', searchTime = 0;
  const portal = document.createElement('div');
  portal.className = 'c2-options-portal';
  portal.hidden = true;
  portal.setAttribute('popover', 'manual');
  const list = document.createElement('div');
  list.className = 'c2-options-list';
  list.id = 'c2-options-list';
  list.setAttribute('role', 'listbox');
  portal.append(list);
  // This sibling of body does not inherit its CSS zoom. Coordinates are screen CSS px.
  document.documentElement.append(portal);

  const scale = () => Number(getComputedStyle(document.body).zoom) || 1;
  function physicalRect(element) {
    const rect = element.getBoundingClientRect(), body = document.body;
    // CEF127 excludes CSS zoom in rects; newer Chromium includes it.
    const ratio = body.getBoundingClientRect().width / parseFloat(getComputedStyle(body).width);
    const factor = Math.abs(ratio - 1) < .02 ? scale() : 1;
    return {left:rect.left*factor, top:rect.top*factor, right:rect.right*factor,
      bottom:rect.bottom*factor, width:rect.width*factor, height:rect.height*factor};
  }
  const unavailable = option => option.disabled || option.hidden ||
    (option.parentElement.tagName === 'OPTGROUP' && option.parentElement.disabled);
  const disabled = control => control.source.matches(':disabled');
  const labelOf = source => source.getAttribute('aria-label') ||
    [...(source.labels || [])].map(label => {
      const copy = label.cloneNode(true);
      copy.querySelectorAll('select,.c2-choice').forEach(node => node.remove());
      return copy.textContent.trim();
    }).filter(Boolean).join(' ') || source.name || 'Selecionar opção';

  function sync(control) {
    const {source, trigger, caption, arrow} = control;
    if (!source.isConnected) {
      if (opened?.control === control) close(false);
      controls.delete(source);
      return;
    }
    const selected = source.selectedOptions[0];
    const text = selected?.textContent.trim() || 'Nenhuma opção disponível';
    if (caption.textContent !== text) caption.textContent = text;
    const off = disabled(control);
    trigger.setAttribute('aria-disabled', String(off));
    trigger.tabIndex = off ? -1 : 0;
    trigger.setAttribute('aria-label', labelOf(source) + ': ' + text);
    // Preserve the existing native select as the layout/form data element.
    const style = getComputedStyle(source);
    for (const name of ['font','letterSpacing','lineHeight','color','backgroundColor',
      'borderTop','borderRight','borderBottom','borderLeft','borderRadius','padding','margin']) {
      if (trigger.style[name] !== style[name]) trigger.style[name] = style[name];
    }
    arrow.style.marginLeft = '8px';
    if (opened?.control === control) {
      const rect = physicalRect(trigger);
      if (off || rect.width === 0 || rect.height === 0 || rect.bottom < 0 || rect.top > innerHeight ||
          source.closest('[hidden]')) close(false);
      else {
        const signature = optionSignature(source);
        if (signature !== opened.signature) renderOptions();
        position();
      }
    }
  }

  function close(restoreFocus = true) {
    if (!opened) return;
    const {control} = opened;
    opened = null;
    control.trigger.setAttribute('aria-expanded', 'false');
    control.trigger.removeAttribute('aria-activedescendant');
    portal.hidden = true;
    if (portal.matches(':popover-open')) portal.hidePopover();
    list.replaceChildren();
    search = '';
    if (restoreFocus && control.source.isConnected && !disabled(control)) control.trigger.focus();
  }

  function optionSignature(source) {
    return JSON.stringify([...source.options].map(option =>
      [option.value, option.textContent, option.selected, unavailable(option), option.hidden]));
  }

  function position() {
    if (!opened) return;
    const {control} = opened, rect = physicalRect(control.trigger), zoom = scale();
    const style = getComputedStyle(control.source);
    list.style.fontFamily = style.fontFamily;
    list.style.fontSize = Math.max(14, parseFloat(style.fontSize) * zoom) + 'px';
    list.style.setProperty('--choice-row-height', Math.max(38, 32 * zoom) + 'px');
    const available = Math.max(80, innerWidth - 16);
    list.style.width = Math.min(available, Math.max(rect.width, 220 * zoom)) + 'px';
    list.style.left = Math.max(8, Math.min(rect.left, innerWidth - list.offsetWidth - 8)) + 'px';
    const below = innerHeight - rect.bottom - 12, above = rect.top - 12;
    const upwards = below < Math.min(240 * zoom, list.scrollHeight) && above > below;
    list.style.maxHeight = Math.min(360 * zoom, Math.max(80, upwards ? above : below)) + 'px';
    const height = list.offsetHeight;
    list.style.top = Math.max(8, Math.min(innerHeight - height - 8,
      upwards ? rect.top - height - 5 : rect.bottom + 5)) + 'px';
  }

  function highlight(index, scroll = true) {
    if (!opened) return;
    opened.index = index;
    list.querySelectorAll('[role=option]').forEach(row => {
      const active = Number(row.dataset.choiceIndex) === index;
      row.classList.toggle('c2-option-active', active);
      if (active) {
        opened.control.trigger.setAttribute('aria-activedescendant', row.id);
        if (scroll) row.scrollIntoView({block:'nearest'});
      }
    });
  }

  function renderOptions() {
    const {control} = opened, source = control.source, previous = opened.index;
    opened.signature = optionSignature(source);
    list.replaceChildren();
    list.setAttribute('aria-label', labelOf(source));
    let group = null;
    [...source.options].forEach((option, index) => {
      if (option.hidden || option.parentElement.hidden) return;
      if (option.parentElement.tagName === 'OPTGROUP' && option.parentElement !== group) {
        group = option.parentElement;
        const title = document.createElement('div');
        title.className = 'c2-option-group';
        title.textContent = group.label;
        list.append(title);
      }
      const row = document.createElement('div');
      row.className = 'c2-choice-option';
      row.setAttribute('role', 'option');
      row.id = 'c2-option-' + control.id + '-' + index;
      row.dataset.choiceIndex = String(index);
      row.dataset.choiceValue = option.value;
      row.setAttribute('aria-selected', String(option.selected));
      row.setAttribute('aria-disabled', String(unavailable(option)));
      const mark = document.createElement('span');
      mark.className = 'c2-choice-mark';
      mark.setAttribute('aria-hidden', 'true');
      mark.textContent = option.selected ? '✓' : '';
      const text = document.createElement('span');
      text.textContent = option.textContent;
      row.append(mark, text);
      row.addEventListener('pointermove', () => { if (!unavailable(option)) highlight(index, false); });
      row.addEventListener('click', event => {
        event.preventDefault(); event.stopPropagation();
        if (!unavailable(option)) commit(index);
      });
      list.append(row);
    });
    if (!list.children.length) {
      const empty = document.createElement('div');
      empty.className = 'c2-choice-empty';
      empty.textContent = 'Nenhuma opção disponível';
      empty.setAttribute('role', 'status');
      list.append(empty);
    }
    const selected = source.selectedIndex;
    highlight(source.options[previous] && !unavailable(source.options[previous]) ? previous : selected, false);
  }

  function open(control) {
    if (disabled(control)) return;
    document.dispatchEvent(new Event('cosmos2-close-suggestions'));
    if (opened?.control === control) { close(); return; }
    close(false);
    opened = {control, index:control.source.selectedIndex, signature:null};
    control.trigger.setAttribute('aria-expanded', 'true');
    portal.hidden = false;
    portal.showPopover();
    renderOptions(); position(); highlight(opened.index);
    control.trigger.focus({preventScroll:true});
  }

  function commit(index) {
    if (!opened) return;
    const {control} = opened, source = control.source, option = source.options[index];
    if (disabled(control) || !option || unavailable(option)) return;
    const changed = source.selectedIndex !== index;
    source.selectedIndex = index;
    close();
    sync(control);
    if (changed) {
      source.dispatchEvent(new Event('input', {bubbles:true}));
      source.dispatchEvent(new Event('change', {bubbles:true}));
      sync(control);
    }
  }

  function enhance(source) {
    if (controls.has(source) || source.multiple || source.size > 1 || source.dataset.nativeOptions === 'true') return;
    const wrapper = document.createElement('span');
    wrapper.className = 'c2-choice';
    const trigger = document.createElement('span');
    trigger.className = 'c2-choice-trigger';
    trigger.id = (source.id || 'choice-' + (++serial)) + '-choice';
    trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-controls', list.id);
    trigger.tabIndex = 0;
    const caption = document.createElement('span'), arrow = document.createElement('span');
    caption.className = 'c2-choice-caption';
    arrow.className = 'c2-choice-arrow';
    arrow.textContent = '▾'; arrow.setAttribute('aria-hidden', 'true');
    trigger.append(caption, arrow);
    source.before(wrapper); wrapper.append(source, trigger);
    source.classList.add('c2-choice-source');
    source.tabIndex = -1;
    source.setAttribute('aria-hidden', 'true');
    const control = {source, wrapper, trigger, caption, arrow, id:++serial};
    controls.set(source, control);
    trigger.addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); open(control); });
    trigger.addEventListener('keydown', event => {
      if (disabled(control)) return;
      if (['ArrowDown','ArrowUp','Enter',' '].includes(event.key)) {
        event.preventDefault(); event.stopPropagation(); open(control);
      } else if (event.key.length === 1 && !event.ctrlKey && !event.altKey && !event.metaKey) {
        event.preventDefault(); event.stopPropagation(); open(control); typeahead(event.key);
      }
    });
    source.addEventListener('focus', () => trigger.focus({preventScroll:true}));
    source.addEventListener('change', () => sync(control));
    source.addEventListener('invalid', event => { event.preventDefault(); trigger.focus(); if (!opened) open(control); });
    sync(control);
  }

  function typeahead(character) {
    if (!opened) return;
    const now = Date.now(); search = now - searchTime > 700 ? character : search + character; searchTime = now;
    const plain = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
    const options = [...opened.control.source.options];
    const index = options.findIndex(option => !unavailable(option) && plain(option.textContent.trim()).startsWith(plain(search)));
    if (index >= 0) highlight(index);
  }

  portal.addEventListener('pointerdown', event => {
    event.stopPropagation();
    if (event.target === portal) { event.preventDefault(); close(); }
  });
  portal.addEventListener('wheel', event => event.stopPropagation());
  document.addEventListener('keydown', event => {
    if (!opened) return;
    if (event.key === 'Tab') { close(false); return; }
    const handled = ['Escape','ArrowDown','ArrowUp','Home','End','Enter',' '].includes(event.key) ||
      (event.key.length === 1 && !event.ctrlKey && !event.altKey && !event.metaKey);
    if (!handled) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (event.key === 'Escape') return close();
    if (event.key === 'Enter' || event.key === ' ') return commit(opened.index);
    if (event.key.length === 1) return typeahead(event.key);
    const options = [...opened.control.source.options], enabled = options.map((option,index) =>
      unavailable(option) ? -1 : index).filter(index => index >= 0);
    if (!enabled.length) return;
    let at = enabled.indexOf(opened.index);
    if (event.key === 'Home') at = 0;
    else if (event.key === 'End') at = enabled.length - 1;
    else at = Math.max(0, Math.min(enabled.length - 1, at + (event.key === 'ArrowUp' ? -1 : 1)));
    highlight(enabled[at]);
  }, true);
  document.addEventListener('click', event => {
    const label = event.target.closest('label');
    if (!label || event.target.closest('.c2-choice') || event.target.closest('button,a,input,textarea')) return;
    const source = label.control || label.querySelector('select');
    const control = controls.get(source);
    if (control) { event.preventDefault(); open(control); }
  });

  document.addEventListener('cosmos2-close-choices', () => close(false));
  const discover = () => document.querySelectorAll('select').forEach(enhance);
  discover();
  let queued = false;
  const observer = new MutationObserver(records => {
    if (records.every(record => portal.contains(record.target) || record.target.closest?.('.c2-choice-trigger'))) return;
    if (!queued) {
      queued = true;
      requestAnimationFrame(() => { queued = false; discover(); controls.forEach(sync); });
    }
  });
  observer.observe(document.body, {subtree:true, childList:true, attributes:true,
    attributeFilter:['disabled','hidden','selected','label','value','aria-label']});
  // selectedIndex/value assignments do not emit DOM mutations.
  const timer = setInterval(() => controls.forEach(sync), 180);
  window.addEventListener('resize', () => controls.forEach(sync));
  document.addEventListener('scroll', () => { if (opened) position(); }, true);
  window.addEventListener('pagehide', () => { clearInterval(timer); observer.disconnect(); close(false); }, {once:true});
})();
