// Phase 4: login -> open 报表设计工作台 -> open a report into designer -> confirm spreadsheet.
import { chromium } from 'playwright'
const SHOTS = '/Users/nanomesh/Workspace/presentation/.e2e-shots'
const log = (...a) => console.log(...a)

const browser = await chromium.launch({ channel: 'chrome', headless: false })
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message))
page.on('console', (m) => { if (m.type() === 'error') errors.push('CONSOLE.ERR: ' + m.text()) })

async function login() {
  await page.goto('http://localhost:8080/portal/', { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(1200)
  if (page.url().includes('login')) {
    await page.fill('#username', 'admin'); await page.fill('#password', 'cmxadmin')
    await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(()=>{}), page.click('button[type=submit]')])
    await page.waitForTimeout(2500)
  }
  await page.waitForSelector('cmx-portal-app', { timeout: 20000 }).catch(()=>{})
  await page.waitForTimeout(2000)
}

// click the SMALLEST element whose trimmed textContent === exact (deep shadow search)
async function deepClickExact(exact) {
  const handle = await page.evaluateHandle((exact) => {
    let best = null
    const visit = (root) => {
      for (const el of root.querySelectorAll('*')) {
        const t = (el.textContent || '').trim().replace(/\s+/g, ' ')
        if (t === exact) { if (!best || (el.textContent||'').length < (best.textContent||'').length) best = el }
        if (el.shadowRoot) visit(el.shadowRoot)
      }
    }
    visit(document)
    return best
  }, exact)
  const el = handle.asElement()
  if (!el) return false
  await el.scrollIntoViewIfNeeded().catch(()=>{})
  await el.click({ timeout: 5000 }).catch(async () => { await el.evaluate(n => n.click()) })
  return true
}

await login()

// expand 报表 group first (click its header). The group leaf items exist but collapsed.
log('== expand 报表 group ==')
await deepClickExact('报表').catch(()=>{})
await page.waitForTimeout(800)

log('== open 报表设计工作台 ==')
const ok = await deepClickExact('报表设计工作台')
log('clicked 报表设计工作台:', ok)
await page.waitForTimeout(3500)
await page.screenshot({ path: `${SHOTS}/06-design-workbench.png` })

// The workbench lists reports with 打开(open) buttons -> data-act="open" data-code=...
// Dump report cards + open buttons found in shadow DOM.
const cards = await page.evaluate(() => {
  const out = []
  const visit = (root) => {
    for (const el of root.querySelectorAll('[data-act="open"], [data-code], .rpt-card')) {
      out.push({ tag: el.tagName.toLowerCase(), act: el.getAttribute('data-act'), code: el.getAttribute('data-code'), text: (el.textContent||'').trim().replace(/\s+/g,' ').slice(0,40) })
    }
    for (const el of root.querySelectorAll('*')) if (el.shadowRoot) visit(el.shadowRoot)
  }
  visit(document)
  return out.slice(0, 60)
})
log('== report open buttons / cards ==')
cards.forEach(c => log('  ', JSON.stringify(c)))

log('== ERRORS ==', errors.length); errors.slice(0,15).forEach(e=>log('  ',e))
log('DONE phase4')
await browser.close()
