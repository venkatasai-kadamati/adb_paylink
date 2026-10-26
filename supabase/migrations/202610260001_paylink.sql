-- PayLink core: five base relations. Amounts are integer USD cents.
BEGIN;
CREATE SCHEMA IF NOT EXISTS paylink;
REVOKE ALL ON SCHEMA paylink FROM PUBLIC;
CREATE TABLE paylink.users (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 username text NOT NULL UNIQUE CHECK (username ~ '^[a-z][a-z0-9_]{2,29}$'),
 email text NOT NULL UNIQUE CHECK (email = lower(email) AND email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
 phone text UNIQUE CHECK (phone IS NULL OR phone ~ '^\+[1-9][0-9]{7,14}$'),
 full_name text NOT NULL CHECK (length(full_name) BETWEEN 1 AND 80),
 password_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE paylink.banks (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 routing_number text NOT NULL UNIQUE CHECK (routing_number ~ '^[0-9]{9}$'),
 name text NOT NULL
);
CREATE TABLE paylink.bank_accounts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 bank_id uuid NOT NULL REFERENCES paylink.banks(id),
 account_number text NOT NULL CHECK (account_number ~ '^[0-9]{12}$'),
 account_type text NOT NULL CHECK (account_type IN ('checking','savings')),
 label text NOT NULL CHECK (length(label) BETWEEN 1 AND 60),
 balance_cents bigint NOT NULL DEFAULT 100000 CHECK (balance_cents BETWEEN 0 AND 900000000000000),
 opening_balance_cents bigint NOT NULL DEFAULT 100000 CHECK (opening_balance_cents BETWEEN 0 AND 900000000000000),
 active boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(bank_id, account_number)
);
CREATE TABLE paylink.account_holders (
 user_id uuid NOT NULL REFERENCES paylink.users(id),
 account_id uuid NOT NULL REFERENCES paylink.bank_accounts(id),
 joined_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(user_id, account_id)
);
CREATE INDEX account_holders_account_idx ON paylink.account_holders(account_id);
CREATE TABLE paylink.transfers (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 initiated_by uuid NOT NULL REFERENCES paylink.users(id),
 source_account_id uuid NOT NULL REFERENCES paylink.bank_accounts(id),
 destination_account_id uuid NOT NULL REFERENCES paylink.bank_accounts(id),
 amount_cents bigint NOT NULL CHECK (amount_cents BETWEEN 1 AND 100000000),
 memo text NOT NULL DEFAULT '' CHECK (length(memo) <= 140),
 idempotency_key uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK (source_account_id <> destination_account_id),
 UNIQUE(initiated_by, idempotency_key)
);
CREATE INDEX transfers_source_time_idx ON paylink.transfers(source_account_id, created_at DESC, id DESC);
CREATE INDEX transfers_destination_time_idx ON paylink.transfers(destination_account_id, created_at DESC, id DESC);
-- Supabase Data API roles get no access. Backend is the only trust boundary.
ALTER TABLE paylink.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE paylink.banks ENABLE ROW LEVEL SECURITY;
ALTER TABLE paylink.bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE paylink.account_holders ENABLE ROW LEVEL SECURITY;
ALTER TABLE paylink.transfers ENABLE ROW LEVEL SECURITY;

CREATE FUNCTION paylink.execute_transfer(
 p_actor uuid, p_source uuid, p_destination uuid, p_amount bigint,
 p_memo text, p_key uuid
) RETURNS paylink.transfers
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, paylink AS $$
DECLARE prior paylink.transfers; result paylink.transfers;
DECLARE source_balance bigint; account_count integer;
BEGIN
 IF p_actor IS NULL OR p_key IS NULL OR p_amount IS NULL OR p_source IS NULL OR p_destination IS NULL OR p_memo IS NULL THEN
  RAISE EXCEPTION 'Required transfer field missing' USING ERRCODE='P0001';
 END IF;
 IF p_amount < 1 OR p_amount > 100000000 OR p_source = p_destination OR length(p_memo) > 140 THEN
  RAISE EXCEPTION 'Invalid transfer details' USING ERRCODE='P0001';
 END IF;
 -- Serialize same-user/key retries, including those targeting different account pairs.
 PERFORM pg_advisory_xact_lock(hashtextextended(p_actor::text || ':' || p_key::text, 0));
 SELECT * INTO prior FROM paylink.transfers WHERE initiated_by=p_actor AND idempotency_key=p_key;
 IF FOUND THEN
  IF prior.source_account_id <> p_source OR prior.destination_account_id <> p_destination
     OR prior.amount_cents <> p_amount OR prior.memo <> p_memo THEN
   RAISE EXCEPTION 'Idempotency key already used for different details' USING ERRCODE='P0001';
  END IF;
  RETURN prior;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM paylink.account_holders WHERE user_id=p_actor AND account_id=p_source) THEN
  RAISE EXCEPTION 'You do not own the source account' USING ERRCODE='P0001';
 END IF;
 -- Total UUID order prevents deadlocks for opposing transfers. All account mutations use this function.
 PERFORM id FROM paylink.bank_accounts WHERE id IN (p_source,p_destination) ORDER BY id FOR UPDATE;
 SELECT count(*) INTO account_count FROM paylink.bank_accounts WHERE id IN(p_source,p_destination) AND active;
 IF account_count <> 2 THEN RAISE EXCEPTION 'Both accounts must exist and be active' USING ERRCODE='P0001'; END IF;
 SELECT balance_cents INTO source_balance FROM paylink.bank_accounts WHERE id=p_source;
 IF source_balance < p_amount THEN RAISE EXCEPTION 'Insufficient funds' USING ERRCODE='P0001'; END IF;
 UPDATE paylink.bank_accounts SET balance_cents=balance_cents-p_amount WHERE id=p_source;
 UPDATE paylink.bank_accounts SET balance_cents=balance_cents+p_amount WHERE id=p_destination;
 INSERT INTO paylink.transfers(initiated_by,source_account_id,destination_account_id,amount_cents,memo,idempotency_key)
 VALUES(p_actor,p_source,p_destination,p_amount,p_memo,p_key) RETURNING * INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION paylink.execute_transfer(uuid,uuid,uuid,bigint,text,uuid) FROM PUBLIC;

CREATE FUNCTION paylink.open_account(p_actor uuid,p_bank uuid,p_type text,p_label text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,paylink AS $$
DECLARE new_id uuid;
BEGIN
 -- Serialize simulated faucet allocation: max 4 accounts per person.
 PERFORM id FROM paylink.users WHERE id=p_actor FOR UPDATE;
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
REVOKE ALL ON FUNCTION paylink.open_account(uuid,uuid,text,text) FROM PUBLIC;
COMMIT;
