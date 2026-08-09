// Playwright check script for preview overlay and button/key synthesis
// Usage: node .github/scripts/check-preview.js <URL>
const { chromium } = require('playwright');

async function run(url){
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const result = { url, ok: false, errors: [], overlay: false, buttons: {}, timestamp: new Date().toISOString() };
  try{
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    result.httpStatus = resp && resp.status();

    // wait for either overlay or timeout
    try{
      await page.waitForSelector('.touch-controls', { timeout: 15000 });
      result.overlay = true;
    } catch(e){
      result.overlay = false;
      result.errors.push('overlay-missing');
    }

    // prepare key capture in page
    await page.evaluate(() => {
      window._preview_monitor = { down: [], up: [] };
      window.addEventListener('keydown', (e) => { try{ window._preview_monitor.down.push({key:e.key, code:e.code, keyCode:e.keyCode, t: Date.now()}); } catch(e){} });
      window.addEventListener('keyup', (e) => { try{ window._preview_monitor.up.push({key:e.key, code:e.code, keyCode:e.keyCode, t: Date.now()}); } catch(e){} });
    });

    const ids = ['touch-left','touch-right','touch-thrust','touch-fire'];
    const mapping = { 'touch-left': 'ArrowLeft', 'touch-right': 'ArrowRight', 'touch-thrust': 'ArrowUp', 'touch-fire': ' ' };

    for(const id of ids){
      const entry = { found: false, sawDown: false, sawUp: false, seenKeys: [] };
      const el = await page.$('#' + id);
      if(!el){
        entry.found = false;
        result.buttons[id] = entry;
        result.errors.push(`button-missing:${id}`);
        continue;
      }
      entry.found = true;

      // clear previous captures
      await page.evaluate(() => { if(window._preview_monitor){ window._preview_monitor.down.length = 0; window._preview_monitor.up.length = 0; } });

      // prefer touch if available; simulate both touch and mouse to be robust
      try{
        await el.click({ force: true, timeout: 5000 });
      } catch(e){
        // best-effort: dispatch events directly in page
        await page.evaluate((iid) => {
          const el = document.getElementById(iid); if(!el) return;
          el.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));
          setTimeout(()=>el.dispatchEvent(new MouseEvent('mouseup',{bubbles:true})),50);
        }, id);
      }

      // wait briefly for events
      await page.waitForTimeout(120);

      const captured = await page.evaluate(() => ({down: window._preview_monitor ? window._preview_monitor.down.slice() : [], up: window._preview_monitor ? window._preview_monitor.up.slice() : [] }));
      entry.sawDown = captured.down.length > 0;
      entry.sawUp = captured.up.length > 0;
      entry.seenKeys = captured.down.concat(captured.up).map(x=>x.key);
      // basic check for expected key
      entry.expected = mapping[id];
      entry.expectedSeen = entry.seenKeys.some(k => k === mapping[id]);

      if(!entry.expectedSeen) result.errors.push(`no-key:${id}:${mapping[id]}`);
      result.buttons[id] = entry;
    }

    result.ok = result.errors.length === 0 && result.overlay === true;
  } catch (err){
    result.errors.push(err && err.message ? err.message : String(err));
  } finally{
    try{ await browser.close(); } catch(e){}
  }
  return result;
}

(async ()=>{
  const url = process.argv[2] || process.env.PREVIEW_URL;
  if(!url){ console.error('Usage: node check-preview.js <URL> (or set PREVIEW_URL env)'); process.exit(2); }
  const r = await run(url);
  console.log(JSON.stringify(r, null, 2));
  if(!r.ok){ console.error('Preview check failed'); process.exit(1); }
  console.log('Preview check passed');
  process.exit(0);
})();
