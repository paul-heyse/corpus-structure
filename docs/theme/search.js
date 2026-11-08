// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Paul Heyse

const bundle = new URL('../pagefind/', import.meta.url);
const toolbar = document.querySelector('.right-buttons') || document.body;
const startup = document.createElement('div');
startup.className = 'search-startup';
startup.innerHTML = '<button type="button" disabled>Search documentation</button><span role="status"></span>';
toolbar.prepend(startup);

function offerReload(status, button) {
  status.textContent = 'Documentation search could not load.';
  button.textContent = 'Reload to retry';
  button.hidden = false;
  button.disabled = false;
  button.onclick = () => window.location.reload();
}

function mountSearch({ configureInstance, getInstanceManager }) {
  configureInstance('default', {
    bundlePath: bundle.pathname,
    baseUrl: new URL('../', bundle).pathname,
  });
  const instance = getInstanceManager().getInstance('default');
  const modal = document.createElement('pagefind-modal');
  modal.setAttribute('reset-on-close', '');
  modal.innerHTML = `
    <pagefind-modal-header><pagefind-input></pagefind-input></pagefind-modal-header>
    <pagefind-modal-body>
      <p class="search-status" role="status"></p>
      <button class="search-retry" type="button" hidden>Reload to retry</button>
      <label class="search-scope">Search in
        <select aria-label="Search scope" disabled></select>
      </label>
      <pagefind-summary></pagefind-summary><pagefind-results></pagefind-results>
    </pagefind-modal-body>
    <pagefind-modal-footer><pagefind-keyboard-hints></pagefind-keyboard-hints></pagefind-modal-footer>`;
  const scope = modal.querySelector('select');
  const status = modal.querySelector('.search-status');
  const retry = modal.querySelector('.search-retry');
  const scopes = document.querySelector('meta[name="doc-scopes"]')?.content.split(',')
    ?? ['Current', 'Everything'];
  for (const name of scopes) scope.append(new Option(name, name));
  scope.addEventListener('change', () => {
    instance.triggerFilter('scope', scope.value === 'Everything' ? [] : [scope.value]);
  });

  let generation = 0;
  let filtersReady = false;
  let failed = false;
  let ready = false;
  let loading;
  instance.on('filters', () => { filtersReady = true; });
  const fail = () => {
    failed = true;
    offerReload(status, retry);
  };
  // Pagefind can report an import failure without rejecting the load promise.
  instance.on('error', () => {
    if (!ready) fail();
  });

  new MutationObserver(() => {
    const dialog = modal.querySelector('dialog');
    const opened = ++generation;
    if (!dialog?.open || failed) return;
    const input = modal.querySelector('pagefind-input input');
    scope.value = 'Current';
    input.readOnly = true;
    scope.disabled = true;
    if (!ready) status.textContent = 'Loading documentation search…';
    loading ??= instance.triggerLoad().then(() => {
      if (!filtersReady && !failed) fail();
      ready = filtersReady && !failed;
    }).catch(fail);
    void loading.then(() => {
      if (!ready || opened !== generation || !dialog.open) return;
      instance.triggerFilter('scope', ['Current']);
      input.readOnly = false;
      scope.disabled = false;
      status.textContent = '';
    });
  }).observe(modal, { subtree: true, attributes: true, attributeFilter: ['open'] });

  document.body.append(modal);
  const trigger = document.createElement('pagefind-modal-trigger');
  trigger.setAttribute('placeholder', 'Search documentation');
  startup.replaceWith(trigger);
}

try {
  await import(new URL('pagefind-component-ui.js', bundle));
  mountSearch(window.PagefindComponents);
} catch {
  offerReload(startup.querySelector('[role="status"]'), startup.querySelector('button'));
}
