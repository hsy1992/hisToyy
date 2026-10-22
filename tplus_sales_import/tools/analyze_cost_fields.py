"""Read-only investigation of local T+ cost fields; never prints credentials."""
import json
import sys
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.configuration import DatabaseConfig
import pyodbc


def main():
    cfg = DatabaseConfig.load(ROOT / 'config.ini')
    if cfg.host != '127.0.0.1' or cfg.database != 'UFDATA_999_1015':
        raise RuntimeError('Expected local analysis database')
    con = pyodbc.connect(cfg.connection_string(), autocommit=True, timeout=6)
    con.timeout = 30
    def query(label, sql, *params):
        cur = con.execute(sql, *params)
        cols = [x[0] for x in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        print(label, json.dumps(rows, ensure_ascii=False, default=str))
        return rows
    query('DATABASE', 'SELECT DB_NAME() AS name')
    if len(sys.argv) > 1:
        query('CUSTOM', Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
    else:
        query('MATCH', '''SELECT h.code AS voucher,h.voucherdate,h.idmarketingorgan,h.exchangerate,
           b.* FROM dbo.SA_SaleDelivery_b b JOIN dbo.SA_SaleDelivery h ON h.id=b.idSaleDeliveryDTO
           WHERE b.costPrice=22.12 OR b.LatestCost=22.12159222''')
        query('CANDIDATE_TABLES', '''SELECT t.name,SUM(p.rows) AS row_count FROM sys.tables t
            JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1)
            WHERE t.name LIKE '%Stock%' OR t.name LIKE '%Book%' OR t.name LIKE '%InvPrice%'
               OR t.name LIKE '%Option%' OR t.name IN ('ST_RDRecord','ST_RDRecord_b')
            GROUP BY t.name ORDER BY t.name''')
        query('COLUMNS', '''SELECT t.name AS table_name,c.name,ty.name AS type_name,c.scale,
           CAST(ep.value AS nvarchar(1000)) AS description FROM sys.tables t
           JOIN sys.columns c ON c.object_id=t.object_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id
           LEFT JOIN sys.extended_properties ep ON ep.major_id=t.object_id AND ep.minor_id=c.column_id AND ep.name='MS_Description'
           WHERE t.name IN ('ST_CurrentStock','ST_SubsidiaryBook','ST_RDRecord','ST_RDRecord_b',
            'ST_MarketingOrganInvPrice','AA_InventoryEntity')
           ORDER BY t.name,c.column_id''')
        query('COST_ROWS', '''SELECT h.code AS voucher,h.voucherdate,h.idmarketingorgan,h.exchangerate,
          b.id,b.idinventory,b.idwarehouse,b.quantity,b.baseQuantity,b.saleOutQuantity,
          b.origDiscountPrice,b.discountPrice,b.origDiscountAmount,b.discountAmount,
          b.origTaxPrice,b.taxRate,b.costPrice,b.costAmount,b.LatestCost,
          b.SingleInvGrossProfit,b.GrossProfit,b.GrossProfitRate,b.adjustAmount,
          b.idunit,b.idbaseunit,b.isManualCost,b.CostPriceGetType
          FROM dbo.SA_SaleDelivery_b b JOIN dbo.SA_SaleDelivery h ON h.id=b.idSaleDeliveryDTO
          WHERE b.costPrice IS NOT NULL OR b.LatestCost IS NOT NULL ORDER BY b.id''')
    con.close()

if __name__ == '__main__':
    main()
