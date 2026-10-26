-- Review the first query, then substitute ONE exact account UUID below in SQL Editor.
SELECT a.id,a.label,u.username FROM paylink.bank_accounts a
JOIN paylink.account_holders h ON h.account_id=a.id JOIN paylink.users u ON u.id=h.user_id
WHERE u.username='sai';

-- Explicit example template, intentionally commented until the account is selected:
-- INSERT INTO paylink.account_holders(user_id,account_id)
-- SELECT id,'REPLACE_WITH_SELECTED_ACCOUNT_UUID'::uuid FROM paylink.users
-- WHERE username='siddhardth' ON CONFLICT DO NOTHING;
-- Do not link all accounts or expose account-management SQL to the browser.
