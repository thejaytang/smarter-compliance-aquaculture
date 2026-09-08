// Read-only evidence UI. Source identity and version are resolved by the server.
export async function showEvidence(container, sourceId, api, {page = 1} = {}) {
  const request = Symbol('evidence');
  container.evidenceRequest = request;
  container.replaceChildren();
  const status = document.createElement('p');
  status.className = 'muted';
  status.textContent = 'Opening the registered local original…';
  container.append(status);
  try {
    const result = await api('/api/preview/' + encodeURIComponent(sourceId));
    if (!container.isConnected || container.evidenceRequest !== request) return;
    status.textContent = result.label || result.message;
    if (result.kind === 'pdf') {
      const url = new URL(result.url, location.origin);
      if (url.origin !== location.origin || !url.pathname.startsWith('/api/pdf/')) throw Error('The original document address is invalid.');
      url.hash = 'page=' + Math.max(1, Math.floor(page));
      const controls = document.createElement('div');
      controls.className = 'row evidence-controls';
      const label = document.createElement('span');
      label.textContent = result.filename;
      const open = document.createElement('a');
      open.href = url.href; open.target = '_blank'; open.rel = 'noopener noreferrer';
      open.textContent = 'Open in new window ↗';
      const close = document.createElement('button');
      close.type = 'button'; close.textContent = 'Close original';
      close.onclick = () => { container.evidenceRequest = null; container.replaceChildren(); };
      controls.append(label, open, close);
      const frame = document.createElement('iframe');
      frame.className = 'pdf-reader'; frame.src = url.href;
      frame.title = 'Full local PDF with page, zoom and search controls';
      container.append(controls, frame);
    } else if (result.text) {
      const text = document.createElement('div');
      text.className = 'preview'; text.textContent = result.text;
      container.append(text);
    }
  } catch (error) {
    if (container.isConnected && container.evidenceRequest === request) {
      status.textContent = error.message;
      status.setAttribute('role', 'alert');
    }
  }
}
