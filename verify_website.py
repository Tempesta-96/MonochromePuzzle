from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1200,'height':1200})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(Path('docs/index.html').resolve().as_uri())
    assert page.locator('#pieces button').count() == 2
    results = page.evaluate('''() => LEVELS.map(level => ({level:level.level, valid:matches(computeGrid(level,level.solution),level.target), fits:level.pieces.every((cells,i)=>cells.every(([r,c])=>r+level.solution[i][1]<level.grid_size&&c+level.solution[i][0]<level.grid_size))}))''')
    assert all(r['valid'] and r['fits'] for r in results)
    for number in [0, 1, 50, 100]:
        page.select_option('#level', str(number))
        solutions = page.evaluate('data.solution')
        size = page.evaluate('data.grid_size')
        for i, (x,y) in enumerate(solutions):
            page.locator('#pieces button').nth(i).click()
            page.locator('#board button').nth(y*size+x).click()
        assert 'Pattern matched' in page.locator('#status').inner_text()
        page.click('#reset')
        assert page.evaluate('positions.every(p=>p===null)')
    page.select_option('#level', '1')
    page.click('#hint')
    assert page.locator('#board .origin').count() == 1
    page.click('#solution')
    assert page.locator('#solution').get_attribute('aria-pressed') == 'true'
    page.click('#reset')
    x,y = page.evaluate('data.solution[0]')
    size = page.evaluate('data.grid_size')
    source=page.locator('#pieces button').nth(0).bounding_box()
    dest=page.locator('#board button').nth(y*size+x).bounding_box()
    page.mouse.move(source['x']+source['width']/2, source['y']+source['height']/2)
    page.mouse.down()
    page.mouse.move(dest['x']+dest['width']/2, dest['y']+dest['height']/2, steps=8)
    page.mouse.up()
    print('DRAG', page.evaluate('positions'), [x,y], page.locator('#status').inner_text()); assert page.evaluate('positions[0]') == [x,y]
    page.reload()
    assert '4 / 101' in page.locator('#progress').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path='website-preview.png', full_page=True)
    assert not errors, errors
    browser.close()
    print('PASS: all 101 targets and bounds; 4 solved levels; reset, hints, solution, mouse drag, saved progress, mobile layout; no JavaScript errors')


