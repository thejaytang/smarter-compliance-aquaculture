"""Describe visual losses in the offline HTML reading view, without fetching assets.

The caller supplies a derived BeautifulSoup tree with original anchors already
assigned. This never edits the saved original or enables source styles/scripts.
"""
import re


_RASTER_DATA = re.compile(r'^data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+$', re.I)
_VISUAL_LABELS = {
    'svg': 'Vector figure', 'math': 'Mathematical expression',
    'canvas': 'Canvas content', 'iframe': 'Embedded frame',
    'object': 'Embedded object', 'embed': 'Embedded object',
    'audio': 'Audio content', 'video': 'Video content',
}


def describe_html_display(soup):
    """Mark unsupported visual regions before the normal sanitizer removes them.

    Count outermost visual regions, not their nested implementation elements.
    Original text outside those regions and its anchors remain untouched.
    """
    resources = {
        'external_stylesheets': len(soup.select('link[rel~=stylesheet][href]')),
        'embedded_styles_removed': len(soup.find_all('style')),
        'inline_styles_removed': len(soup.select('[style]')),
        'unavailable_images': sum(not _RASTER_DATA.fullmatch(node.get('src', ''))
                                  for node in soup.find_all('img')),
    }
    omissions = []
    for node in list(soup.find_all(list(_VISUAL_LABELS))):
        if node.parent is None or any(parent.name in _VISUAL_LABELS for parent in node.parents):
            continue
        kind = node.name
        anchor = node.get('data-original-anchor')
        message = f'{_VISUAL_LABELS[kind]} cannot be displayed in this reading view. Compare this location with the saved original.'
        placeholder = soup.new_tag('span')
        if anchor:
            placeholder['data-original-anchor'] = anchor
        placeholder.string = '[' + message + ']'
        node.replace_with(placeholder)
        omissions.append({'kind': kind, 'anchor': anchor, 'message': message})
    warnings = []
    if resources['external_stylesheets']:
        warnings.append(f"{resources['external_stylesheets']} external stylesheet references are not loaded. The saved page's original layout cannot be reproduced by this reading view.")
    if resources['unavailable_images']:
        warnings.append(f"{resources['unavailable_images']} image references cannot be displayed offline. Their locations are marked in the reading view.")
    if omissions:
        warnings.append(f'{len(omissions)} unsupported visual regions are marked in the reading view. Their absence must not be treated as empty source content.')
    return {'mode': 'reflowed_reading_view', 'original_layout_preserved': False,
            'resources': resources, 'omissions': omissions, 'warnings': warnings}
