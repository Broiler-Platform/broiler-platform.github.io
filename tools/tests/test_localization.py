"""Check language URLs, shared navigation and untranslated-document fallback."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build
import verify


class LocalizationTests(unittest.TestCase):
    def render(self, path):
        meta, body = build.read_source(build.PAGES / path)
        meta.update(path=path, lang='de' if path.startswith('de/') else 'en')
        return build.render(build.SHELL.read_text(encoding='utf-8'), meta, body)

    def test_every_german_page_has_reciprocal_language_links(self):
        for source in sorted((build.PAGES / 'de').rglob('*.html')):
            relative = build.rel_of(source)
            original = relative.removeprefix('de/')
            with self.subTest(path=relative):
                german, english = self.render(relative), self.render(original)
                self.assertIn('<html lang="de">', german)
                self.assertIn('<html lang="en">', english)
                self.assertIn(f'href="{build.page_url(original)}" lang="en"', german)
                self.assertIn(f'href="{build.page_url(relative)}" lang="de"', english)
                for html in (german, english):
                    self.assertIn(f'hreflang="de" href="{build.BASE_URL.rstrip("/")}{build.page_url(relative)}"', html)
                    self.assertNotIn('%%', html)

    def test_german_navigation_and_accessibility_are_localized(self):
        page = self.render('de/applications/writer.html')
        self.assertIn('href="/de/applications.html" aria-current="page"', page)
        self.assertIn('href="/de/"', page)
        self.assertIn('aria-label="Hauptnavigation"', page)
        self.assertIn('aria-label="Farbschema wechseln"', page)
        self.assertIn('Zum Inhalt springen', page)
        self.assertIn('Sicherheit und Grenzen', page)
        self.assertIn('href="/architecture.html"', page)
        self.assertIn('Architektur (Englisch)', page)
        self.assertIn('href="/assets/css/site.css"', page)

    def test_untranslated_document_links_to_german_overview_honestly(self):
        page = self.render('architecture.html')
        self.assertIn('href="/de/" lang="de"', page)
        self.assertIn('Deutsch · Übersicht', page)
        self.assertNotIn('hreflang="de" href="https://', page)
        self.assertIn('rel="canonical" href="https://broiler-platform.github.io/architecture.html"', page)

    def test_nested_german_pages_are_verified_and_404_is_not_indexed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'de/applications/writer.html'
            target.parent.mkdir(parents=True)
            target.write_text('test', encoding='utf-8')
            self.assertEqual(verify.pages(Path(directory)), [target])
        sitemap = build.build_sitemap(['index.html', 'de/index.html', '404.html', 'de/404.html'])
        self.assertIn('<loc>https://broiler-platform.github.io/de/</loc>', sitemap)
        self.assertNotIn('404', sitemap)
