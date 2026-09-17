"""HTML v2: one source text inventory with typed DOM structure and evidence."""
from typing import Literal
from pydantic import Field
from .source import Strict, Snapshot

class HtmlAtom(Strict):
    id: str
    node_id: str
    text_index: int = Field(ge=1)
    text: str
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'

class HtmlNode(Strict):
    id: str
    locator: str
    parent_id: str | None
    ordinal: int
    tag: str
    kind: str
    attributes: dict[str, str | list[str]]
    role: Literal['content','metadata','navigation','control'] = 'content'
    heading_level: int | None = None
    section_id: str | None = None
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'

class HtmlOmission(Strict):
    locator: str
    tag: str
    reason: Literal['non_content_script','non_content_style','comment']
    text_sha256: str

class HtmlCell(Strict):
    node_id: str
    row: int
    column: int | None
    rowspan: int | None
    colspan: int | None
    is_header: bool
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'

class HtmlTable(Strict):
    node_id: str
    row_count: int
    column_count: int | None
    cells: list[HtmlCell]
    confidence: float | None = None
    issues: list[str] = Field(default_factory=list)
    review_policy: Literal['review_required'] = 'review_required'

class HtmlList(Strict):
    node_id: str
    ordered: bool
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'
    item_node_ids: list[str]
    source_label_node_ids: list[str] = Field(default_factory=list)

class HtmlLink(Strict):
    node_id: str
    target: str
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'
    target_node_ids: list[str]
    relation: Literal['internal','external','embedded_footnote','modal_footnote','blocked_scheme']
    status: Literal['resolved','external_not_fetched','missing','ambiguous','blocked']

class HtmlDocument(Strict):
    schema_version: Literal['html-document/2'] = 'html-document/2'
    source: Snapshot
    parser_version: str
    config_hash: str
    profile: str
    encoding: str
    root_node_ids: list[str]
    nodes: list[HtmlNode]
    atoms: list[HtmlAtom]
    tables: list[HtmlTable]
    lists: list[HtmlList]
    links: list[HtmlLink]
    omitted: list[HtmlOmission]
    issues: list[str]
    confidence: float | None = None
    review_policy: Literal['review_required'] = 'review_required'
    requirement_status: Literal['not_extracted'] = 'not_extracted'
    display_policy: Literal['static_snapshot_all_dom_variants_preserved'] = 'static_snapshot_all_dom_variants_preserved'

# These are reviewable policy data. Extractor uses CSS; independent verifier uses XPath.
HTML_PROFILES = {
    'lovdata': {
        'identity_css': '#documentMeta',
        'identity_xpath': '//*[@id="documentMeta"]',
        'roots_css': ['head > title', '#documentMeta', '#documentBody'],
        'roots_xpath': ['/html/head/title', '//*[@id="documentMeta"]', '//*[@id="documentBody"]'],
    },
    'asc': {
        'identity_css': 'main .sidebar--filters',
        'identity_xpath': '//main//*[contains(concat(" ",normalize-space(@class)," ")," sidebar--filters ")]',
        'roots_css': ['head > title', 'main'],
        'roots_xpath': ['/html/head/title', '//main'],
    },
    'fiskeridirektoratet': {
        'identity_css': 'main#main [data-portal-region="header"].fd-default-region',
        'identity_xpath': '//main[@id="main"]//*[@data-portal-region="header" and contains(concat(" ",normalize-space(@class)," ")," fd-default-region ")]',
        'roots_css': ['head > title', 'main#main'],
        'roots_xpath': ['/html/head/title', '//main[@id="main"]'],
    },
    'miljodirektoratet': {
        'identity_css': 'main.t_master-page__main',
        'identity_xpath': '//main[contains(concat(" ",normalize-space(@class)," ")," t_master-page__main ")]',
        'roots_css': ['head > title', 'main#main'],
        'roots_xpath': ['/html/head/title', '//main[@id="main"]'],
    },
    'mattilsynet': {
        'identity_css': 'main.page-layout[data-testid]',
        'identity_xpath': '//main[@data-testid and contains(concat(" ",normalize-space(@class)," ")," page-layout ")]',
        'roots_css': ['head > title', 'main#main'],
        'roots_xpath': ['/html/head/title', '//main[@id="main"]'],
    },
}
