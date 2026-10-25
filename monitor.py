#!/usr/bin/env python3
"""VCA visible-button monitor. Secrets are injected as environment variables by Actions."""
import argparse
import json
import os
import re
import smtplib
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.request import Request, urlopen

PRODUCT_URL = 'https://www.vancleefarpels.com/us/en/collections/jewelry/alhambra/vcard35600---vintage-alhambra-bracelet-5-motifs.html'
PRODUCT_NAME = 'Van Cleef & Arpels Vintage Alhambra 5 motifs · VCARD35600'
ARTIFACTS = Path('artifacts')


def required(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ValueError('Missing secret: ' + name)
    return value


def send_email(test=False):
    sender = required('GMAIL_USER')
    password = ''.join(required('GMAIL_APP_PASSWORD').split())
    recipient = required('EMAIL_TO')
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = ('【测试邮件】' if test else '【补货提醒】') + PRODUCT_NAME
    msg.set_content(
        ('这是一封测试邮件，不代表商品有货。' if test else
         '检测到商品页面的 ADD TO BAG 按钮可见，请立即打开商品页核实并手动购买。')
        + '\n\n' + PRODUCT_URL + '\n\n检测时间（UTC）：'
        + datetime.now(timezone.utc).isoformat()
        + '\n页面显示可能变化，通知不保证结账成功。'
    )
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30,
                          context=ssl.create_default_context()) as smtp:
        smtp.login(sender, password)
        refused = smtp.send_message(msg)
        if refused:
            raise RuntimeError('Email recipient rejected')


def send_bark(test=False):
    # POST keeps the device key out of request URLs and ordinary access logs.
    payload = {
        'device_key': required('BARK_KEY'),
        'title': '【响铃测试】VCA' if test else '【补货提醒】VCA 有货',
        'body': '测试警报，不代表有货。' if test else PRODUCT_NAME + '\nADD TO BAG 已可见，点击查看。',
        'level': 'critical', 'call': '1', 'volume': '5', 'sound': 'alarm',
        'group': 'VCA-VCARD35600', 'url': PRODUCT_URL,
    }
    request = Request('https://api.day.app/push',
                      data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
        if response.status != 200 or data.get('code') != 200:
            # Never print server payloads, keys, credentials or raw exceptions.
            raise RuntimeError('Bark rejected request')


def notify(channels, test=False):
    """Attempt both independently, even if one fails. No automatic duplicate retries."""
    funcs = {'email': send_email, 'bark': send_bark}
    failed = False
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {name: pool.submit(funcs[name], test) for name in channels}
        for name, future in jobs.items():
            try:
                future.result()
                print(f'{name}: accepted by server (check device/inbox for delivery)', flush=True)
            except Exception as exc:
                failed = True
                print(f'{name}: FAILED ({type(exc).__name__}); check Secrets and service settings', flush=True)
    return 1 if failed else 0


def visible_action(page, text):
    """Check EVERY matching action; hidden desktop/mobile duplicates are common."""
    pattern = re.compile(r'^\s*' + r'\s+'.join(re.escape(s) for s in text.split()) + r'\s*$', re.I)
    for role in ('button', 'link'):
        matches = page.get_by_role(role, name=pattern, include_hidden=True)
        for index in range(matches.count()):
            item = matches.nth(index)
            if not item.is_visible():
                continue
            # Playwright considers opacity:0 visible; reject transparent ancestors too.
            if item.evaluate('''el => {
                for (let p = el; p; p = p.parentElement) {
                    const s = getComputedStyle(p);
                    if (s.display === 'none' || s.visibility === 'hidden' ||
                        s.visibility === 'collapse' || Number(s.opacity) === 0) return false;
                }
                return true;
            }'''):
                return True
    return False


def read_status(page):
    # User policy: visible ADD TO BAG wins, even if disabled or both actions appear.
    if visible_action(page, 'ADD TO BAG'):
        return 'IN_STOCK'
    if visible_action(page, 'ORDER BY PHONE'):
        return 'OUT_OF_STOCK'
    return 'UNKNOWN'


def wait_status(page, seconds=35):
    # Give the hydrated page a chance to change its initial out-of-stock placeholder.
    deadline = time.monotonic() + seconds
    while True:
        status = read_status(page)
        if status == 'IN_STOCK' or time.monotonic() >= deadline:
            return status
        page.wait_for_timeout(1000)


def save_evidence(page, status, error_type=None):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    report = {'status': status, 'time_utc': datetime.now(timezone.utc).isoformat(),
              'product_url': PRODUCT_URL, 'error_type': error_type}
    if page is not None:
        try:
            page.screenshot(path=str(ARTIFACTS / 'page.png'), full_page=True, timeout=15000)
            report['screenshot'] = 'page.png'
        except Exception as exc:
            report['screenshot_error'] = type(exc).__name__
    (ARTIFACTS / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def check_product(dry_run=False):
    page = None
    browser = None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(locale='en-US', timezone_id='America/Los_Angeles',
                                              viewport={'width': 1440, 'height': 1100})
                page = context.new_page()
                page.set_default_timeout(8000)
                response = page.goto(PRODUCT_URL, wait_until='domcontentloaded', timeout=60000)
                if response is not None and response.status >= 400:
                    raise RuntimeError('Product HTTP error')
                # Do not use networkidle: analytics connections may never finish.
                page.wait_for_timeout(12000)
                # Only a known cookie control is clicked; never shopping controls.
                cookie = page.locator('#onetrust-reject-all-handler')
                if cookie.count() and cookie.first.is_visible():
                    cookie.first.click(timeout=3000)
                status = wait_status(page)
                save_evidence(page, status)
            except Exception as exc:
                save_evidence(page, 'ERROR', type(exc).__name__)
                print(f'ERROR: {type(exc).__name__}; see artifacts', flush=True)
                return 1
            finally:
                if browser is not None:
                    browser.close()
    except Exception as exc:
        save_evidence(None, 'ERROR', type(exc).__name__)
        print(f'ERROR: {type(exc).__name__}; check browser installation', flush=True)
        return 1
    print('STATUS: ' + status, flush=True)
    if status == 'UNKNOWN':
        print('Neither action is visible; screenshot saved. This is NOT out of stock.', flush=True)
        return 1
    if status == 'IN_STOCK' and not dry_run:
        return notify(('bark', 'email'))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--test-email', action='store_true', help='Send only a test email; no browser')
    mode.add_argument('--test-bark', action='store_true', help='Send a critical ringing test; no browser')
    mode.add_argument('--test-all', action='store_true', help='Test both notification channels; no browser')
    mode.add_argument('--dry-run', action='store_true', help='Check real page and screenshot, send nothing')
    args = parser.parse_args(argv)
    if args.test_email:
        return notify(('email',), test=True)
    if args.test_bark:
        return notify(('bark',), test=True)
    if args.test_all:
        return notify(('bark', 'email'), test=True)
    return check_product(dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
