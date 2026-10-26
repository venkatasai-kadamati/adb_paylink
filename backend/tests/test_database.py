"""Integration checks on real PostgreSQL, isolated by unique fixture identities."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from pathlib import Path
import pytest
import psycopg
from psycopg import errors
from dotenv import dotenv_values
C=dotenv_values(Path(__file__).resolve().parents[2]/'.env')

@pytest.fixture
def case():
    actor,other,bank,a,b= [uuid4() for _ in range(5)]
    suffix=uuid4().hex[:12]
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        c.execute('INSERT INTO paylink.users(id,username,email,full_name,password_hash) VALUES(%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s)',
          (actor,'t'+suffix,'t'+suffix+'@test.dev','Test','unused',other,'u'+suffix,'u'+suffix+'@test.dev','Other','unused'))
        c.execute('INSERT INTO paylink.banks(id,name,routing_number) VALUES(%s,%s,%s)',(bank,'Test Bank',str(int(suffix,16)%1000000000).zfill(9)))
        for id,num in [(a,'111111111111'),(b,'222222222222')]:
            c.execute('INSERT INTO paylink.bank_accounts(id,bank_id,account_number,account_type,label,balance_cents,opening_balance_cents) VALUES(%s,%s,%s,%s,%s,10000,10000)',(id,bank,num,'checking','Test account'))
        c.execute('INSERT INTO paylink.account_holders(user_id,account_id) VALUES(%s,%s),(%s,%s)',(actor,a,other,b))
    yield actor,other,bank,a,b
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        c.execute('DELETE FROM paylink.transfers WHERE source_account_id IN(%s,%s) OR destination_account_id IN(%s,%s)',(a,b,a,b))
        c.execute('DELETE FROM paylink.account_holders WHERE user_id IN(%s,%s)',(actor,other))
        c.execute('DELETE FROM paylink.bank_accounts WHERE bank_id=%s',(bank,))
        c.execute('DELETE FROM paylink.users WHERE id IN(%s,%s)',(actor,other))
        c.execute('DELETE FROM paylink.banks WHERE id=%s',(bank,))

def transfer(actor,a,b,amount,key=None,memo='test',url=None):
    with psycopg.connect(url or C['DATABASE_URL']) as c:
        c.execute('SET statement_timeout=10000')
        return c.execute('SELECT id FROM paylink.execute_transfer(%s,%s,%s,%s,%s,%s)',(actor,a,b,amount,memo,key or uuid4())).fetchone()[0]

def balances(a,b):
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        return dict(c.execute('SELECT id,balance_cents FROM paylink.bank_accounts WHERE id IN(%s,%s)',(a,b)).fetchall())

def test_atomic_transfer_and_conservation(case):
    u,_,_,a,b=case; transfer(u,a,b,2300)
    assert balances(a,b)=={a:7700,b:12300}

def test_rollback_on_insufficient_funds(case):
    u,_,_,a,b=case
    with pytest.raises(errors.RaiseException,match='Insufficient'):transfer(u,a,b,10001)
    assert balances(a,b)=={a:10000,b:10000}
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        assert c.execute('SELECT count(*) FROM paylink.transfers WHERE source_account_id=%s',(a,)).fetchone()[0]==0

def test_concurrent_duplicate_requests_once(case):
    u,_,_,a,b=case; key=uuid4()
    with ThreadPoolExecutor(8) as workers:
        ids=list(workers.map(lambda _:transfer(u,a,b,1200,key),range(8)))
    assert len(set(ids))==1
    assert balances(a,b)=={a:8800,b:11200}

def test_conflicting_idempotency_payload(case):
    u,_,_,a,b=case;key=uuid4();transfer(u,a,b,100,key)
    with pytest.raises(errors.RaiseException,match='different details'):transfer(u,a,b,101,key)
    assert balances(a,b)=={a:9900,b:10100}

def test_concurrent_spending_cannot_overdraw(case):
    u,_,_,a,b=case
    def attempt(_):
        try:transfer(u,a,b,7000);return True
        except errors.RaiseException:return False
    with ThreadPoolExecutor(2) as workers: result=list(workers.map(attempt,range(2)))
    assert sorted(result)==[False,True]
    assert balances(a,b)=={a:3000,b:17000}

def test_opposing_transfers_without_deadlock(case):
    u,v,_,a,b=case
    with ThreadPoolExecutor(8) as workers:
        list(workers.map(lambda i:transfer(u,a,b,100) if i%2==0 else transfer(v,b,a,100),range(20)))
    assert balances(a,b)=={a:10000,b:10000}

def test_non_owner_cannot_spend(case):
    _,v,_,a,b=case
    with pytest.raises(errors.RaiseException,match='do not own'):transfer(v,a,b,1)
    assert balances(a,b)=={a:10000,b:10000}

def test_inactive_destination(case):
    u,_,_,a,b=case
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:c.execute('UPDATE paylink.bank_accounts SET active=false WHERE id=%s',(b,))
    with pytest.raises(errors.RaiseException,match='active'):transfer(u,a,b,1)
    assert balances(a,b)=={a:10000,b:10000}

@pytest.mark.parametrize('amount',[0,-1,100000001])
def test_invalid_amount(case,amount):
    u,_,_,a,b=case
    with pytest.raises(errors.RaiseException):transfer(u,a,b,amount)

def test_no_direct_balance_updates(case):
    _,_,_,a,_=case
    with psycopg.connect(C['DATABASE_URL']) as c:
        with pytest.raises(errors.InsufficientPrivilege):c.execute('UPDATE paylink.bank_accounts SET balance_cents=999999 WHERE id=%s',(a,))

def test_foreign_key_and_balance_constraint(case):
    u,_,_,a,b=case
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        with pytest.raises(errors.CheckViolation):c.execute('UPDATE paylink.bank_accounts SET balance_cents=-1 WHERE id=%s',(a,))
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        with pytest.raises(errors.ForeignKeyViolation):c.execute('INSERT INTO paylink.account_holders(user_id,account_id) VALUES(%s,%s)',(u,uuid4()))

def test_joint_owner_can_spend(case):
    u,v,_,a,b=case
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:c.execute('INSERT INTO paylink.account_holders(user_id,account_id) VALUES(%s,%s)',(v,a))
    transfer(v,a,b,500)
    assert balances(a,b)=={a:9500,b:10500}

def test_transaction_rollback_after_debits(case):
    # An enclosing transaction fails AFTER the function updates balances; all changes must roll back.
    u,_,_,a,b=case
    with pytest.raises(errors.DivisionByZero):
        with psycopg.connect(C['DATABASE_URL']) as c:
            c.execute('SELECT paylink.execute_transfer(%s,%s,%s,%s,%s,%s)',(u,a,b,1000,'rollback',uuid4()))
            c.execute('SELECT 1/0')
    assert balances(a,b)=={a:10000,b:10000}

def test_same_account_rejected(case):
    u,_,_,a,_=case
    with pytest.raises(errors.RaiseException,match='Invalid'):transfer(u,a,a,1)

def test_credit_limit_failure_rolls_back_debit(case):
    u,_,_,a,b=case
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        c.execute('UPDATE paylink.bank_accounts SET balance_cents=900000000000000 WHERE id=%s',(b,))
    with pytest.raises(errors.CheckViolation): transfer(u,a,b,100)
    assert balances(a,b)=={a:10000,b:900000000000000}
    with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
        assert c.execute('SELECT count(*) FROM paylink.transfers WHERE source_account_id=%s',(a,)).fetchone()[0]==0
