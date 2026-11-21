#!/usr/bin/env python3
"""GitHub Actions에서 실행: 시세/공포탐욕지수를 가져와 data/all.json 하나로 저장.
- 서버(러너)에서 가져오므로 브라우저 CORS 문제가 없다.
- 사이트는 all.json 한 파일만 읽어서 빠르다.
- 일부 구간이 실패해도 대체 구간으로 채우고, 그래도 없으면 이전 값을 유지한다.
표준 라이브러리만 사용."""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
os.makedirs(DATA, exist_ok=True)
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
DAY = 864e5


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def get_json(url, headers=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={'User-Agent': UA, 'Accept': 'application/json', **(headers or {})})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            print(f'  재시도 {i + 1}/{tries}: {url[:90]} -> {e}')
            time.sleep(3 * (i + 1))
    return None


def yahoo(sym, rng, interval):
    q = f'/v8/finance/chart/{urllib.parse.quote(sym)}?range={rng}&interval={interval}'
    j = get_json('https://query1.finance.yahoo.com' + q) or \
        get_json('https://query2.finance.yahoo.com' + q, tries=2)
    time.sleep(0.8)   # 요청 간격을 둬서 차단(429) 방지
    try:
        res = j['chart']['result'][0]
        ts = res.get('timestamp') or []
        cl = res['indicators']['quote'][0].get('close') or []
    except Exception:
        return None
    pts = [[int(t) * 1000, round(c, 4)] for t, c in zip(ts, cl) if c is not None]
    return (pts, res.get('meta', {})) if len(pts) > 1 else None


def recent(pts, days, now):
    return [p for p in pts if p[0] >= now - days * DAY]


def weekly(pts):
    """일봉 -> 주봉(각 주의 마지막 값). 5년 차트 용량을 줄인다."""
    out, last = [], None
    for p in pts:
        key = datetime.fromtimestamp(p[0] / 1000, timezone.utc).isocalendar()[:2]
        if out and key == last:
            out[-1] = p
        else:
            out.append(p)
        last = key
    return out


def build_stock(sym, name, old):
    e = {'name': name, 'updated': old.get('updated'),
         'price': old.get('price'), 'prev': old.get('prev'),
         'ranges': dict(old.get('ranges', {}))}      # 실패한 구간은 이전 값 유지
    now = time.time() * 1000
    got = False

    r = yahoo(sym, '1d', '5m')
    if r:
        got = True
        e['ranges']['d1'] = r[0]
        e['price'] = r[1].get('regularMarketPrice')
        e['prev'] = r[1].get('chartPreviousClose') or r[1].get('previousClose')

    hourly = yahoo(sym, '1mo', '1h')
    if hourly:
        got = True
        e['ranges']['d7'] = recent(hourly[0], 7, now)

    # 5년 일봉 한 번으로 30일/1년/5년을 모두 만든다 (요청 수↓, 누락↓)
    daily = yahoo(sym, '5y', '1d')
    if daily:
        got = True
        d = daily[0]
        e['ranges']['y1'] = recent(d, 365, now)
        e['ranges']['d30'] = recent(d, 30, now)
        e['ranges']['y5'] = weekly(d)
    else:                                              # 대체 경로
        y1 = yahoo(sym, '1y', '1d')
        if y1:
            got = True
            e['ranges']['y1'] = y1[0]
            e['ranges']['d30'] = recent(y1[0], 30, now)
        elif hourly:
            e['ranges']['d30'] = recent(hourly[0], 30, now)
        y5 = yahoo(sym, '5y', '1wk')
        if y5:
            got = True
            e['ranges']['y5'] = y5[0]

    mx = yahoo(sym, 'max', '1mo')
    if mx:
        got = True
        e['ranges']['max'] = mx[0]

    if e['price'] is None or e['prev'] is None:        # 현재가 정보가 없으면 일봉에서 보충
        for k in ('y1', 'd30', 'd7'):
            p = e['ranges'].get(k)
            if p and len(p) > 1:
                e['price'], e['prev'] = p[-1][1], p[-2][1]
                break

    if not got:
        return None
    e['updated'] = now_iso()
    return e


def build_fg():
    j = get_json('https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2020-09-18',
                 headers={'Referer': 'https://edition.cnn.com/', 'Origin': 'https://edition.cnn.com'})
    try:
        n = j['fear_and_greed']
        hist = j['fear_and_greed_historical']['data']
        return {'updated': now_iso(),
                'now': {'score': n['score'], 'rating': n['rating'], 'previous_close': n['previous_close']},
                'points': [[int(d['x']), round(d['y'], 2)] for d in hist]}
    except Exception:
        return None


def main():
    with open(os.path.join(ROOT, 'symbols.json'), encoding='utf-8') as f:
        symbols = json.load(f)
    path = os.path.join(DATA, 'all.json')
    try:
        with open(path, encoding='utf-8') as f:
            old = json.load(f)
    except Exception:
        old = {}
    out = {'updated': now_iso(), 'symbols': symbols,
           'fg': old.get('fg'), 'stocks': {}}
    ok = {}

    print('CNN 공포탐욕지수')
    fg = build_fg()
    if fg:
        out['fg'] = fg
    ok['FG'] = bool(fg)

    for s in symbols:
        print(s['s'])
        prev = old.get('stocks', {}).get(s['s'], {})
        e = build_stock(s['s'], s['n'], prev)
        ok[s['s']] = bool(e)
        if e:
            out['stocks'][s['s']] = e
        elif prev:
            out['stocks'][s['s']] = prev               # 전부 실패하면 이전 데이터 유지

    print('\n결과:', {k: ('OK' if v else '실패') for k, v in ok.items()})
    for k, v in out['stocks'].items():
        miss = [r for r in ('d1', 'd7', 'd30', 'y1', 'y5', 'max') if r not in v['ranges']]
        if miss:
            print(f'  {k}: 없는 구간 {miss}')
    if not any(ok.values()):
        sys.exit(1)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('저장:', path, os.path.getsize(path) // 1024, 'KB')


if __name__ == '__main__':
    main()
