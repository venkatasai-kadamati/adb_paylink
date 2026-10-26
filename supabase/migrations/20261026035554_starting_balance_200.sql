-- New accounts receive $200. Existing balances and opening balances are preserved.
ALTER TABLE paylink.bank_accounts ALTER COLUMN balance_cents SET DEFAULT 20000;
ALTER TABLE paylink.bank_accounts ALTER COLUMN opening_balance_cents SET DEFAULT 20000;
