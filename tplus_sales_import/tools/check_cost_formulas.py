import json
from pathlib import Path
from decimal import Decimal as D, ROUND_HALF_UP, ROUND_DOWN, getcontext
getcontext().prec = 60
root = Path(__file__).resolve().parents[1]
data = {line.split(' ', 1)[0]: json.loads(line.split(' ', 1)[1]) for line in
        (root / 'outputs/cost_fields_raw.txt').read_text(encoding='utf-8').splitlines()}
rows = data['COST_ROWS']
def n(row, name):
    return D(row[name]) if row[name] is not None else None
def check(label, target, calc):
    tests = []
    for r in rows:
        if r[target] is None:
            continue
        try:
            v = calc(r)
        except (TypeError, ZeroDivisionError, AttributeError):
            continue
        tests.append((r, v, n(r, target)))
    bad = [(r['id'], str(v), str(actual)) for r, v, actual in tests if v != actual]
    print(label, 'tested', len(tests), 'match', len(tests)-len(bad), 'bad', bad[:8])
for price in ('origDiscountPrice', 'discountPrice'):
    check('Single-' + price, 'SingleInvGrossProfit', lambda r: (n(r,price)-n(r,'LatestCost')).quantize(D('.00000001'),rounding=ROUND_HALF_UP))
for rounding in (ROUND_HALF_UP, ROUND_DOWN):
    check('Gross-'+rounding, 'GrossProfit', lambda r: (n(r,'SingleInvGrossProfit')*n(r,'quantity')).quantize(D('.01'),rounding=rounding))
    check('Rate-'+rounding, 'GrossProfitRate', lambda r: (n(r,'SingleInvGrossProfit')/n(r,'origDiscountPrice')).quantize(D('.0001'),rounding=rounding))
    check('CostAmount-'+rounding,'costAmount', lambda r: (n(r,'costPrice')*n(r,'baseQuantity')).quantize(D('.01'),rounding=rounding))
check('CostPrice=roundLatestCost2', 'costPrice',lambda r: n(r,'LatestCost').quantize(D('.01'),rounding=ROUND_HALF_UP))
check('CostPrice=costAmount/baseQuantity8','costPrice',lambda r:(n(r,'costAmount')/n(r,'baseQuantity')).quantize(D('.00000001'),rounding=ROUND_HALF_UP))
for rounding in (ROUND_HALF_UP, ROUND_DOWN):
    check('CostPrice=costAmount/baseQuantity6-'+rounding,'costPrice',lambda r:(n(r,'costAmount')/n(r,'baseQuantity')).quantize(D('.000001'),rounding=rounding))
print('unit_equal',sum(r['idunit']==r['idbaseunit'] for r in rows),len(rows))
print('example', json.dumps(rows[0],ensure_ascii=False))
print('user_example', 'P=',D('22.12159222')+D('13.27663787'), 'ratio=',D('13.27663787')/(D('22.12159222')+D('13.27663787')))
