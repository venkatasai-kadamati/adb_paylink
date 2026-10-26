-- Run as the schema owner in the Supabase SQL Editor (or psql).
-- All examples are read-only. The benchmark rolls all synthetic rows back.

-- 1. Joins and aggregation: count owners without duplicating account balances.
SELECT b.name AS bank, count(*) AS accounts, sum(a.balance_cents)/100.0 AS total_usd
FROM paylink.banks b JOIN paylink.bank_accounts a ON a.bank_id=b.id
GROUP BY b.id,b.name ORDER BY total_usd DESC;

-- 2. Many-to-many: find jointly owned accounts (HAVING).
SELECT a.id,a.label,count(*) AS owners,string_agg(u.username, ', ' ORDER BY u.username) AS usernames
FROM paylink.bank_accounts a
JOIN paylink.account_holders h ON h.account_id=a.id
JOIN paylink.users u ON u.id=h.user_id
GROUP BY a.id,a.label HAVING count(*)>1;

-- 3. Integrity reconciliation. Returns zero rows when every stored balance agrees with history.
WITH deltas AS (
 SELECT source_account_id AS account_id,-amount_cents AS delta FROM paylink.transfers
 UNION ALL
 SELECT destination_account_id,amount_cents FROM paylink.transfers
), expected AS (
 SELECT a.id,a.label,a.balance_cents,a.opening_balance_cents+coalesce(sum(d.delta),0) AS expected_cents
 FROM paylink.bank_accounts a LEFT JOIN deltas d ON d.account_id=a.id
 GROUP BY a.id
)
SELECT * FROM expected WHERE balance_cents<>expected_cents;

-- 4. Window functions: deterministic running balance for Sai's Everyday checking.
WITH target AS (
 SELECT a.id,a.opening_balance_cents FROM paylink.bank_accounts a
 JOIN paylink.account_holders h ON h.account_id=a.id JOIN paylink.users u ON u.id=h.user_id
 WHERE u.username='sai' AND a.label='Everyday checking'
), deltas AS (
 SELECT t.id,t.created_at,t.memo,
 CASE WHEN t.destination_account_id=a.id THEN t.amount_cents ELSE -t.amount_cents END AS change_cents,
 a.opening_balance_cents
 FROM paylink.transfers t JOIN target a ON t.source_account_id=a.id OR t.destination_account_id=a.id
)
SELECT id,created_at,memo,change_cents,
 opening_balance_cents+sum(change_cents) OVER(ORDER BY created_at,id ROWS UNBOUNDED PRECEDING) AS running_balance_cents
FROM deltas ORDER BY created_at,id;

-- 5. Physical inspection. Tiny datasets often correctly choose sequential scans.
SELECT relname,pg_size_pretty(pg_relation_size(relid)) AS heap,
 pg_size_pretty(pg_indexes_size(relid)) AS indexes,n_live_tup
FROM pg_stat_user_tables WHERE schemaname='paylink';

-- 6. Execution plan for account history: composite B-tree (source_account_id,created_at DESC,id DESC).
EXPLAIN (ANALYZE,BUFFERS)
SELECT id,amount_cents,created_at FROM paylink.transfers
WHERE source_account_id=(SELECT a.id FROM paylink.bank_accounts a
 JOIN paylink.account_holders h ON h.account_id=a.id JOIN paylink.users u ON u.id=h.user_id
 WHERE u.username='sai' AND a.label='Everyday checking')
ORDER BY created_at DESC,id DESC LIMIT 20;
