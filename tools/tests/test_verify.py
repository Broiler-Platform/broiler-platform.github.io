"""Website links must recognize verified producer pages as destinations."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify


class ProductLinkTests(unittest.TestCase):
    def test_product_destinations_are_indexed_without_applying_website_shell_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for prefix, version in [('cell', '0.1.0-preview.3'), ('demo', '0.1.0-preview.2'), ('writer', '0.1.0-preview.13')]:
                product = root / prefix / 'releases' / version / 'index.html'
                product.parent.mkdir(parents=True)
                # No website title or metadata: producer pages have their own validation.
                product.write_text('<div id="app">Product</div>', encoding='utf-8')
                entry = root / 'de' / prefix / 'index.html'
                entry.parent.mkdir(parents=True)
                entry.write_text(f'<title>Entry</title><meta name="description" content="Entry"><a href="/{prefix}/releases/{version}/#app">Open</a>', encoding='utf-8')
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(verify.main([directory]), 0)
            # Real missing fragments and missing product files must still fail.
            product.write_text('<div>Product</div>', encoding='utf-8')
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                self.assertEqual(verify.main([directory]), 1)
            self.assertIn('link to missing anchor /writer/releases/0.1.0-preview.13/#app', errors.getvalue())
            product.unlink()
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                self.assertEqual(verify.main([directory]), 1)
            self.assertIn('link to missing page /writer/releases/0.1.0-preview.13/', errors.getvalue())
