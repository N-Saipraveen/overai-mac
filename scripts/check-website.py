"""Check static links and asset references, including project-site relative paths."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
root = Path(__file__).resolve().parents[1] / 'website'
errors = []
class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(); self.path=path; self.ids=set(); self.links=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids: errors.append(f'{self.path}: duplicate id {attrs["id"]}')
            self.ids.add(attrs['id'])
        for key in ('src','href'):
            if key in attrs: self.links.append(attrs[key])
pages={}
for path in root.rglob('*.html'):
    p=Page(path); p.feed(path.read_text()); pages[path.resolve()]=p
for path,p in pages.items():
    for link in p.links:
        u=urlsplit(link)
        if u.scheme or u.netloc: continue
        if u.path.startswith('/'): errors.append(f'{path}: root-relative path breaks project Pages: {link}'); continue
        target=(path.parent/unquote(u.path)).resolve() if u.path else path
        if target.is_dir(): target=target/'index.html'
        if not target.exists(): errors.append(f'{path}: missing {link}')
        elif u.fragment and target in pages and u.fragment not in pages[target].ids: errors.append(f'{path}: missing fragment {link}')
if errors: raise SystemExit('\n'.join(errors))
print(f'Passed: {len(pages)} pages, all local links, fragments and assets resolve.')
