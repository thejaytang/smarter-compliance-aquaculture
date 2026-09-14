// A browser download request is not proof that a file reached the user's disk.
export async function requestPackageDownload(response, env = {}) {
 const doc = env.document || document, Url = env.URL || URL, later = env.setTimeout || setTimeout;
 const filename = response.headers.get('Content-Disposition')?.match(/filename="?([^";]+)"?/)?.[1] || 'collaboration-package.zip';
 const location = response.headers.get('Content-Location');
 let downloadUrl = null, blobUrl = null;
 if (location) {
  const base = new Url(doc.baseURI), target = new Url(location, base);
  const ids = target.searchParams.getAll('id');
  if (target.origin !== base.origin || target.pathname !== '/api/collaboration/collection-download' || target.hash ||
      [...target.searchParams.keys()].some(key => key !== 'id') || ids.length !== 1 ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(ids[0])) {
   throw Error('The saved package download link is invalid. Reopen the package history and retry.');
  }
  downloadUrl = target.pathname + target.search;
  // The POST has completed the freeze. Release its ZIP response; GET reads the
  // same immutable artifact under the current reviewer's session and ownership.
  await response.body?.cancel();
 } else {
  blobUrl = Url.createObjectURL(await response.blob());
 }
 const link = doc.createElement('a');
 link.href = downloadUrl || blobUrl;
 link.download = filename;
 link.hidden = true;
 doc.body.appendChild(link);
 try { link.click(); }
 finally {
  link.remove();
  if (blobUrl) later(() => Url.revokeObjectURL(blobUrl), 30000);
 }
 return {status: 'download_requested', filename, downloadUrl};
}

export function showPackageDownload(container, result, {frozen = false} = {}) {
 const doc = container.ownerDocument;
 container.replaceChildren();
 const message = doc.createElement('span');
 message.textContent = (frozen ? 'Package frozen. ' : '') +
  'Download requested. Check your browser downloads before sharing the file. Your saved work and review status are unchanged.';
 container.appendChild(message);
 if (result?.downloadUrl) {
  const link = doc.createElement('a');
  link.href = result.downloadUrl;
  link.download = result.filename;
  link.textContent = 'Download this saved package';
  container.appendChild(doc.createElement('br'));
  container.appendChild(link);
 } else {
  const recovery = doc.createElement('span');
  recovery.textContent = ' If no file appears, retry the download button; the same frozen package is retained.';
  container.appendChild(recovery);
 }
}
