-- Serialize account allocation while allowing the implicit FK KEY SHARE
-- locks taken by transfer insertion on initiated_by. FOR UPDATE on the user
-- would introduce a user/account lock cycle with joint-owner grants.
CREATE OR REPLACE FUNCTION paylink.open_account(p_actor uuid,p_bank uuid,p_type text,p_label text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,paylink AS $$
DECLARE new_id uuid;
BEGIN
 -- Serialize simulated faucet allocation: max 4 accounts per person.
 PERFORM id FROM paylink.users WHERE id=p_actor FOR NO KEY UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'User not found'; END IF;
 IF (SELECT count(*) FROM paylink.account_holders WHERE user_id=p_actor)>=4 THEN
  RAISE EXCEPTION 'Simulation limit: four accounts per person' USING ERRCODE='P0001';
 END IF;
 INSERT INTO paylink.bank_accounts(bank_id,account_number,account_type,label)
 VALUES(p_bank, lpad((floor(random()*900000000000)::bigint+100000000000)::text,12,'0'),p_type,p_label)
 RETURNING id INTO new_id;
 INSERT INTO paylink.account_holders(user_id,account_id) VALUES(p_actor,new_id);
 RETURN new_id;
END $$;

CREATE OR REPLACE FUNCTION paylink.add_account_holder(p_actor uuid, p_account uuid, p_username text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,paylink AS $$
DECLARE target uuid;
BEGIN
 SELECT id INTO target FROM paylink.users WHERE username=p_username FOR NO KEY UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'User not found' USING ERRCODE='P0001'; END IF;
 PERFORM id FROM paylink.bank_accounts WHERE id=p_account AND active FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Account must exist and be active' USING ERRCODE='P0001'; END IF;
 IF NOT EXISTS(SELECT 1 FROM paylink.account_holders WHERE user_id=p_actor AND account_id=p_account) THEN
  RAISE EXCEPTION 'You do not own this account' USING ERRCODE='P0001';
 END IF;
 IF EXISTS(SELECT 1 FROM paylink.account_holders WHERE user_id=target AND account_id=p_account) THEN
  RETURN target;
 END IF;
 IF (SELECT count(*) FROM paylink.account_holders WHERE user_id=target)>=4 THEN
  RAISE EXCEPTION 'Simulation limit: four accounts per person' USING ERRCODE='P0001';
 END IF;
 INSERT INTO paylink.account_holders(user_id,account_id) VALUES(target,p_account);
 RETURN target;
END $$;
