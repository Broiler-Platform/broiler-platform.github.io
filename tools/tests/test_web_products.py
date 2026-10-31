import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
import build
import web_products as web


class WebProductsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.out=self.root/'site'
        self.out.mkdir()
        (self.out/build.MARKER).touch()
        for _,prefix,_ in web.PRODUCTS.values():
            path=self.out/prefix/'index.html'
            path.parent.mkdir()
            path.write_text('not available yet')

    def fixture(self,product='writer',version='0.1.0-preview.1',release_id=1):
        repo=web.PRODUCTS[product][0]
        source=self.root/('source-'+str(release_id))
        (source/'_framework').mkdir(parents=True)
        entry=b'export const officeInputProtocolVersion = 1;'
        for name,data in {'main.hash.js':entry,'_framework/dotnet.js':b'runtime','_framework/app.wasm':b'\x00asm','broiler.graphics.webassembly.js':b'replay','fonts/test.woff2':b'font','main.hash.js.br':b'compressed'}.items():
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        mapping={'imports':{'./main.js':'./main.hash.js'},'integrity':{'./main.js':'sha256-'+base64.b64encode(hashlib.sha256(entry).digest()).decode()}}
        (source/'index.html').write_text('<script type="importmap">'+json.dumps(mapping)+'</script><script type="module" src="main.hash.js"></script>')
        tag=product+'-web-v'+version
        identity=dict(product=product,productName={'writer':'Writer','cell':'Cells','launcher':'Launcher'}[product],repository=repo,version=version,tag=tag,commit='a'*40,
            sdk="10.0.403",workload="10.0.114/10.0.100",workloadSet=["10.0.403", ""],runtimeMode=web.artifact.MODE,publishTrimmed=True,runAotCompilation=False,dirty=False,verificationOnly=False)
        meta=web.artifact.pack(source,self.root/('release-'+str(release_id)),identity)
        archive=meta.parent/json.loads(meta.read_text())['archive']
        assets=[dict(id=release_id*10+i,name=p.name,size=p.stat().st_size) for i,p in enumerate((meta,archive))]
        data={a['id']:p.read_bytes() for a,p in zip(assets,(meta,archive))}
        release=dict(id=release_id,tag_name=tag,published_at=f'2026-10-{release_id:02}T12:00:00Z',draft=False,assets=assets)
        return release,data

    def test_missing_producers_are_honest_and_strict_mode_fails(self):
        with patch.object(web,'releases',return_value=[]):
            ledger=web.resolve(self.out)
            self.assertEqual(ledger['unavailable'],['cell','launcher','writer'])
            self.assertEqual(json.loads((self.out/'office-web.json').read_text())['status'],'unavailable')
            web.verify(self.out)
            (self.out/'office-web-site.json').unlink()
            with self.assertRaises(ValueError):web.resolve(self.out,required=True)

    def test_newest_web_release_selected_and_older_versions_retained(self):
        old,old_data=self.fixture(release_id=1)
        new,new_data=self.fixture(version='0.2.0-preview.1',release_id=2)
        data={**old_data,**new_data}
        with patch.object(web,'releases',side_effect=lambda repo:[new,old] if repo.endswith('Broiler.Writer') else []),patch.object(web,'asset_bytes',side_effect=lambda repo,a:data[a['id']]),patch.object(web,'source_commit',return_value='a'*40):
            ledger=web.resolve(self.out)
        self.assertEqual(ledger['products'][0]['version'],'0.2.0-preview.1')
        self.assertEqual(len(ledger['history']),2)
        self.assertTrue((self.out/'writer/releases/0.1.0-preview.1/fonts/test.woff2').is_file())
        self.assertIn('./releases/0.2.0-preview.1/',(self.out/'writer/index.html').read_text())
        web.verify(self.out)
        (self.out/'writer/releases/0.2.0-preview.1/main.hash.js').write_text('tampered')
        with self.assertRaises(ValueError):web.verify(self.out)

    def test_damaged_current_release_never_silently_falls_back(self):
        release,data=self.fixture()
        archive=release['assets'][1]
        data[archive['id']]=b'tampered'
        with patch.object(web,'releases',return_value=[release]),patch.object(web,'asset_bytes',side_effect=lambda repo,a:data[a['id']]),patch.object(web,'source_commit',return_value='a'*40):
            with self.assertRaises(ValueError):web.resolve(self.out)

    def test_release_discovery_skips_drafts_and_sorts_publication_time(self):
        rows=[dict(id=1,draft=False,published_at='2026-10-01'),dict(id=2,draft=False,published_at='2026-10-10'),dict(id=3,draft=True,published_at='2026-10-20')]
        with patch.object(web,'api',return_value=rows):self.assertEqual([r['id'] for r in web.releases('example/repo')],[2,1])

    def test_dirty_verification_package_cannot_be_published(self):
        release,data=self.fixture()
        asset=release['assets'][0]
        descriptor=json.loads(data[asset['id']]);descriptor.update(dirty=True,verificationOnly=True,releaseEligible=False)
        data[asset['id']]=json.dumps(descriptor).encode();asset['size']=len(data[asset['id']])
        with patch.object(web,'asset_bytes',side_effect=lambda repo,a:data[a['id']]),patch.object(web,'source_commit',return_value='a'*40):
            with self.assertRaises(ValueError):web.install(web.PRODUCTS['writer'][0],'writer',release,self.out,self.root/'cache')

    def test_complete_suite_catalog_points_to_exact_website_versions(self):
        fixtures={}
        data={}
        for index,product in enumerate(web.PRODUCTS,1):
            release,assets=self.fixture(product=product,release_id=index)
            fixtures[web.PRODUCTS[product][0]]=[release]
            data.update(assets)
        with patch.object(web,'releases',side_effect=lambda repo:fixtures[repo]),patch.object(web,'asset_bytes',side_effect=lambda repo,a:data[a['id']]),patch.object(web,'source_commit',return_value='a'*40):
            ledger=web.resolve(self.out,required=True)
        catalog=json.loads((self.out/'office-web.json').read_text())
        self.assertEqual(catalog['status'],'approved')
        self.assertEqual({p['id'] for p in catalog['products']},{'writer','cell'})
        self.assertEqual(catalog['products'][0]['url'],'https://broiler-platform.github.io/writer/releases/0.1.0-preview.1/')
        self.assertTrue(all(p['entryAvailable'] for p in ledger['products']))
        web.verify(self.out)

    def test_launcher_entry_waits_for_both_editors(self):
        release,data=self.fixture(product='launcher')
        with patch.object(web,'releases',side_effect=lambda repo:[release] if repo==web.PRODUCTS['launcher'][0] else []),patch.object(web,'asset_bytes',side_effect=lambda repo,a:data[a['id']]),patch.object(web,'source_commit',return_value='a'*40):
            ledger=web.resolve(self.out)
        self.assertFalse(ledger['products'][0]['entryAvailable'])
        self.assertEqual((self.out/'demo/index.html').read_text(),'not available yet')

    def test_descriptor_or_tag_identity_mismatch_is_rejected(self):
        release,data=self.fixture()
        with patch.object(web,'asset_bytes',side_effect=lambda repo,a:data[a['id']]),patch.object(web,'source_commit',return_value='b'*40):
            with self.assertRaises(ValueError):web.install(web.PRODUCTS['writer'][0],'writer',release,self.out,self.root/'cache')


if __name__=='__main__':unittest.main()
