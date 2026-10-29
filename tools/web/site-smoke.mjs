// Exercise the site entry routers and same-origin product navigation.
import { chromium, firefox, webkit } from 'playwright';
import { readFile, mkdir, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { tmpdir } from 'node:os';
import assert from 'node:assert/strict';
const [directory,reportFile]=process.argv.slice(2),root=resolve(directory);
const ledger=JSON.parse(await readFile(resolve(root,'office-web-site.json'),'utf8'));
const mime={'.html':'text/html','.js':'text/javascript','.json':'application/json','.wasm':'application/wasm','.css':'text/css','.svg':'image/svg+xml','.woff2':'font/woff2'};
await mkdir(resolve(reportFile,'..'),{recursive:true});
const runs=[];
for(const [name,engine] of Object.entries({chromium,firefox,webkit})) {
    const profile=await mkdtemp(resolve(tmpdir(),'broiler-website-'));
    const context=await engine.launchPersistentContext(profile,{viewport:{width:1280,height:960}}),errors=[],run={engine:name,version:context.browser().version()};
    try {
        await context.route('**/*',async route=>{
            const url=new URL(route.request().url());
            if(['fonts.googleapis.com','fonts.gstatic.com'].includes(url.hostname)) return route.fulfill({contentType:'text/css',body:''});
            if(url.origin!=='https://broiler-platform.github.io') {errors.push('Unexpected destination: '+url.href);return route.abort();}
            const pathname=decodeURIComponent(url.pathname);
            const path=resolve(root,'.'+pathname+(pathname.endsWith('/')?'index.html':''));
            if(!path.startsWith(root+sep))return route.abort();
            try {return route.fulfill({contentType:mime[extname(path)]||'application/octet-stream',body:await readFile(path)});}
            catch {errors.push('Missing asset: '+pathname);return route.fulfill({status:404,body:'Not found'});}
        });
        const page=await context.newPage();
        page.on('pageerror',error=>errors.push(String(error)));
        page.on('console',message=>{if(message.type()==='error')errors.push(message.text()+' '+JSON.stringify(message.location()));});
        await page.goto('https://broiler-platform.github.io/',{waitUntil:'domcontentloaded'});
        for(const path of ['demo','writer','cell'])assert.ok(await page.locator(`a[href="/${path}/"]`).count());
        if(name==='chromium')await page.screenshot({path:reportFile+'.desktop.png'});
        for(const [product,prefix]of [['launcher','demo'],['writer','writer'],['cell','cell']]) {
            await page.goto(`https://broiler-platform.github.io/${prefix}/`,{waitUntil:'domcontentloaded'});
            const row=ledger.products.find(r=>r.product===product);
            if(!row || row.entryAvailable===false) {assert.ok((await page.locator('main').textContent()).includes('not available yet'));continue;}
            await page.waitForURL(row.entryUrl,{waitUntil:'domcontentloaded'});
            if(product==='launcher') {
                await page.waitForFunction(()=>document.body.dataset.ready==='true');
                await page.waitForLoadState('networkidle');
                for(const editor of ledger.products.filter(r=>r.product!=='launcher')) {
                    const link=page.locator(`[data-product="${editor.product}"]`);
                    assert.equal(await link.getAttribute('href'),editor.entryUrl);
                    await link.click({noWaitAfter:true});await page.waitForURL(editor.entryUrl,{waitUntil:'domcontentloaded'});
                    await page.waitForFunction(id=>document.getElementById(id+'-status')?.hidden,editor.product==='cell'?'cells':'writer');
                    await page.waitForLoadState('networkidle');
                    await page.getByRole('link',{name:'Return to Office'}).click({noWaitAfter:true});
                    await page.waitForURL(row.entryUrl,{waitUntil:'domcontentloaded'});
                    await page.waitForFunction(()=>document.body.dataset.ready==='true');
                    await page.waitForLoadState('networkidle');
                }
            } else {
                await page.waitForFunction(id=>document.getElementById(id+'-status')?.hidden,product==='cell'?'cells':'writer');
                await page.waitForLoadState('networkidle');
                assert.equal(await page.getByRole('link',{name:'Return to Office'}).getAttribute('href'),'/demo/');
            }
        }
        if(name==='chromium') {await page.setViewportSize({width:390,height:844});await page.goto('https://broiler-platform.github.io/',{waitUntil:'domcontentloaded'});await page.screenshot({path:reportFile+'.mobile.png'});}
        assert.deepEqual(errors,[]);run.pass=true;
    }catch(error){run.pass=false;run.error=String(error);}
    finally{await context.close();await rm(profile,{recursive:true,force:true,maxRetries:5});runs.push(run);console.log(JSON.stringify(run));}
}
await writeFile(reportFile,JSON.stringify({products:ledger.products.map(p=>({product:p.product,version:p.version})),runs},null,2));
if(runs.some(r=>!r.pass))process.exitCode=1;
