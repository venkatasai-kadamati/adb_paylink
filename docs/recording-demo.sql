-- Read-only recording queries. Replace the example UUID with the receipt ID
-- from the payment you actually record. Do not show credentials or hashes.

-- 1. Exactly five domain tables.
SELECT table_name FROM information_schema.tables
WHERE table_schema='paylink' AND table_type='BASE TABLE' ORDER BY table_name;

-- 2. A real retained hosted acceptance event; replace this ID for a new demo.
SELECT t.id, u.username AS initiated_by, t.amount_cents, t.memo, t.created_at,
       t.source_account_id, t.destination_account_id
FROM paylink.transfers t JOIN paylink.users u ON u.id=t.initiated_by
WHERE t.id='38cf87a4-4f82-44ab-bea1-3011579a6a2c';

-- 3. Current balances for both endpoints. Record balances BEFORE your payment
-- too; these values also include any later successful transfers.
SELECT a.id,a.label,a.balance_cents,a.opening_balance_cents
FROM paylink.bank_accounts a
WHERE a.id IN (
 SELECT source_account_id FROM paylink.transfers
 WHERE id='38cf87a4-4f82-44ab-bea1-3011579a6a2c'
 UNION
 SELECT destination_account_id FROM paylink.transfers
 WHERE id='38cf87a4-4f82-44ab-bea1-3011579a6a2c'
);

-- 4. One shared account, one balance, two holders.
SELECT a.id,a.label,a.balance_cents,string_agg(u.username,', ' ORDER BY u.username) AS owners
FROM paylink.bank_accounts a
JOIN paylink.account_holders h ON h.account_id=a.id
JOIN paylink.users u ON u.id=h.user_id
GROUP BY a.id HAVING count(*)>1;

-- 5. Zero rows means every stored balance reconciles.
WITH delta AS (
 SELECT source_account_id AS id,-amount_cents AS cents FROM paylink.transfers
 UNION ALL
 SELECT destination_account_id,amount_cents FROM paylink.transfers
)
SELECT a.id,a.label,a.balance_cents,
 a.opening_balance_cents+coalesce(sum(d.cents),0) AS expected_cents
FROM paylink.bank_accounts a LEFT JOIN delta d ON d.id=a.id
GROUP BY a.id
HAVING a.balance_cents<>a.opening_balance_cents+coalesce(sum(d.cents),0);
