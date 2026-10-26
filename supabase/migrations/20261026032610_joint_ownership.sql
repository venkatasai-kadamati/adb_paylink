-- Adding a joint holder is a simulation-only grant of equal spending permission.
-- Lock target user before account, matching open_account's user -> account order.
CREATE FUNCTION paylink.add_account_holder(p_actor uuid, p_account uuid, p_username text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,paylink AS $$
DECLARE target uuid;
BEGIN
 SELECT id INTO target FROM paylink.users WHERE username=p_username FOR UPDATE;
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
REVOKE ALL ON FUNCTION paylink.add_account_holder(uuid,uuid,text) FROM PUBLIC;
