from pathlib import Path
from playwright.sync_api import sync_playwright
URL = Path('docs/index.html').resolve().as_uri()

def tray_grab(page, i):
    cells = page.evaluate(f'data.pieces[{i}]')
    r, c = cells[0]
    box = page.locator('#pieces button').nth(i).locator('.shape').bounding_box()
    return box['x'] + c*17 + 8, box['y'] + r*17 + 8, c, r

def destination(page, x, y, c, r):
    size = page.evaluate('data.grid_size')
    box = page.locator('#board').bounding_box()
    step = box['width']/size
    return box['x'] + (x+c+.5)*step, box['y'] + (y+r+.5)*step

def drag_tray(page, i, x, y):
    sx, sy, c, r = tray_grab(page, i)
    dx, dy = destination(page, x, y, c, r)
    page.mouse.move(sx, sy); page.mouse.down()
    assert page.locator('.drag-ghost').count() == 1
    page.mouse.move(dx, dy, steps=8)
    assert page.locator('.drop-preview').count() > 0
    page.mouse.up()
    assert page.evaluate(f'positions[{i}]') == [x, y]
    assert page.locator('.drag-ghost').count() == 0

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1200,'height':1600})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(URL)
    assert page.evaluate('LEVELS.every(l=>matches(computeGrid(l,l.solution),l.target))')
    # Pointer clicks no longer select or place pieces.
    page.locator('#pieces button').first.click()
    page.locator('#board button').first.click()
    assert page.evaluate('positions.every(p=>p===null) && selected===null')
    for number in [0,1,50,100]:
        page.select_option('#level', str(number))
        for i, (x,y) in enumerate(page.evaluate('data.solution')):
            drag_tray(page, i, x, y)
        assert 'Pattern matched' in page.locator('#status').inner_text()
        page.click('#reset')
        assert page.evaluate('positions.every(p=>p===null)')
    page.select_option('#level','1')
    x,y=page.evaluate('data.solution[0]')
    drag_tray(page,0,x,y)
    # Move an already placed piece directly from the board.
    r,c=page.evaluate('data.pieces[0][0]')
    sx,sy=destination(page,x,y,c,r)
    dx,dy=destination(page,0,0,c,r)
    page.mouse.move(sx,sy);page.mouse.down();page.mouse.move(dx,dy,steps=8);page.mouse.up()
    assert page.evaluate('positions[0]')==[0,0]
    # Invalid edge drop restores original placement.
    sx,sy=destination(page,0,0,c,r)
    box=page.locator('#board').bounding_box()
    page.mouse.move(sx,sy);page.mouse.down();page.mouse.move(box['x']+box['width']-2,box['y']+box['height']-2,steps=8);page.mouse.up()
    assert page.evaluate('positions[0]')==[0,0]
    assert 'whole piece must fit' in page.locator('#status').inner_text()
    # Escape cancels a drag and restores the board.
    sx,sy=destination(page,0,0,c,r)
    page.mouse.move(sx,sy);page.mouse.down();page.mouse.move(20,20,steps=8);page.keyboard.press('Escape');page.mouse.up()
    assert page.evaluate('positions[0]')==[0,0]
    assert page.locator('.drag-ghost').count()==0
    # Drop outside to return to the tray.
    page.mouse.move(sx,sy);page.mouse.down();page.mouse.move(20,200,steps=8);page.mouse.up()
    assert page.evaluate('positions[0]') is None
    page.click('#hint');assert page.locator('#board .origin').count()==1
    page.click('#solution');assert page.locator('#solution').get_attribute('aria-pressed')=='true'
    page.reload();assert '4 / 101' in page.locator('#progress').inner_text()
    assert not errors,errors
    # Real touch input, including short-screen automatic scrolling.
    context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
    mobile=context.new_page();mobile.on('pageerror',lambda e:errors.append(str(e)));mobile.goto(URL)
    mobile.locator('#pieces button').first.scroll_into_view_if_needed()
    sx,sy,c,r=tray_grab(mobile,0)
    session=context.new_cdp_session(mobile)
    def touch(kind,x=None,y=None):
        session.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':[] if x is None else [{'x':x,'y':y}]})
    touch('touchStart',sx,sy)
    touch('touchMove',190,35)
    before=mobile.evaluate('scrollY')
    mobile.wait_for_timeout(500)
    assert mobile.evaluate('scrollY') < before
    x,y=mobile.evaluate('data.solution[0]')
    dx,dy=destination(mobile,x,y,c,r)
    touch('touchMove',dx,dy);touch('touchEnd')
    assert mobile.evaluate('positions[0]')==[x,y]
    assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
    mobile.locator('#pieces button').nth(1).scroll_into_view_if_needed()
    sx,sy,c,r=tray_grab(mobile,1)
    touch('touchStart',sx,sy);touch('touchMove',190,35);touch('touchCancel')
    assert mobile.evaluate('positions[1]') is None
    assert mobile.locator('.drag-ghost').count()==0
    assert not errors,errors
    mobile.screenshot(path='website-preview.png',full_page=True)
    browser.close()
    print('PASS: 101 targets; four levels solved by dragging; live snap previews; direct board movement; invalid drop restore; outside return; Escape; hints; saved progress; real touch placement, cancellation, auto-scroll and mobile layout; no JS errors.')
