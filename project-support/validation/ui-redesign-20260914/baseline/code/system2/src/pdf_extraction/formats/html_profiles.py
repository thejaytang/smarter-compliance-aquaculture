"""Conservative profile discovery and independently reviewable content boundaries."""
from ..contracts.html import HTML_PROFILES

class HtmlProfileError(ValueError):
    pass


def select_profile(soup, requested='auto'):
    matches=[key for key, spec in HTML_PROFILES.items() if soup.select(spec['identity_css'])]
    if requested != 'auto':
        matches=[p for p in matches if p==requested]
    if len(matches)!=1:
        raise HtmlProfileError('html_unknown_or_ambiguous_template')
    name=matches[0]; roots=[]
    for selector in HTML_PROFILES[name]['roots_css']:
        found=soup.select(selector)
        # Missing <title> is allowed, but not ambiguous titles or missing content boundaries.
        if len(found)>1 or (selector!='head > title' and not found):
            raise HtmlProfileError('html_missing_or_ambiguous_content_root:'+selector)
        roots.extend(found)
    body=roots[-1]
    if not body.get_text(' ',strip=True):
        raise HtmlProfileError('html_empty_body')
    return name,roots
