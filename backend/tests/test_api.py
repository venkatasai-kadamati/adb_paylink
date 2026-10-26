from fastapi.testclient import TestClient
from backend.app.main import app

def test_authentication_and_csrf():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['database']=='connected'
        assert client.get('/api/accounts').status_code==401
        assert client.post('/api/auth/login',json={'username':'sai','password':'wrong'}).status_code==401
        assert client.post('/api/auth/login',json={'username':'sai','password':'PaylinkDemo!2026'},headers={'Origin':'https://evil.example'}).status_code==403
        r=client.post('/api/auth/login',json={'username':'sai','password':'PaylinkDemo!2026'})
        assert r.status_code==200
        assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
        assert client.get('/api/me').json()['username']=='sai'
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        today=datetime.now(ZoneInfo('America/Chicago')).date()
        assert [d['day'] for d in client.get('/api/insights').json()['weekly']]==[
            (today-timedelta(days=i)).isoformat() for i in range(6,-1,-1)]
        import backend.app.main as main
        with main.pool.connection() as conn:
            assert conn.execute('SHOW TimeZone').fetchone()['TimeZone']=='America/Chicago'
            assert conn.execute('SHOW statement_timeout').fetchone()['statement_timeout']=='10s'
        accounts=client.get('/api/accounts').json()
        assert len(accounts)>=3
        assert all('account_number' not in a for a in accounts)
        assert any(a['holder_count']==2 for a in accounts)
        assert client.get('/api/recipients?q=siddhardth').json()[0]['username']=='siddhardth'
        assert client.get('/api/recipients?q=si').json()==[]
        assert client.get('/api/activity.csv').headers['content-type'].startswith('text/csv')
        assert 'password_hash' not in client.get('/api/me').json()
        assert client.post('/api/auth/logout').status_code==200
        assert client.get('/api/accounts').status_code==401

def test_decimal_amounts_not_coerced():
    with TestClient(app) as c:
        c.post('/api/auth/login',json={'username':'sai','password':'PaylinkDemo!2026'})
        r=c.post('/api/transfers',json={'source_account_id':'00000000-0000-0000-0000-000000000001','destination_account_id':'00000000-0000-0000-0000-000000000002','amount_cents':1.2,'idempotency_key':'00000000-0000-0000-0000-000000000003'})
        assert r.status_code==422

def test_registered_workflow_authorization_insights_csv():
    import csv,io
    from uuid import uuid4
    import psycopg
    from pathlib import Path
    from dotenv import dotenv_values
    C=dotenv_values(Path(__file__).resolve().parents[2]/'.env')
    suffix=uuid4().hex[:10];name='api_'+suffix;other='other_'+suffix
    ids=[];account_ids=[]
    try:
        with TestClient(app) as c, TestClient(app) as d:
            for client,username in [(c,name),(d,other)]:
                r=client.post('/api/auth/register',json={'username':username,'email':username+'@test.dev','full_name':'API Test','password':'Test!workflow2026','phone':None})
                assert r.status_code==201,r.text
                ids.append(r.json()['id'])
            assert c.post('/api/auth/register',json={'username':name,'email':name+'@test.dev','full_name':'API Test','password':'Test!workflow2026'}).status_code==409
            bank=c.get('/api/banks').json()[0]['id']
            for client,label in [(c,'Checking'),(c,'Savings'),(d,'Recipient')]:
                r=client.post('/api/accounts',json={'bank_id':bank,'account_type':'checking','label':label})
                assert r.status_code==201,r.text
                account_ids.append(r.json()['id'])
            a,b,dest=account_ids
            assert d.post(f'/api/accounts/{a}/holders',json={'username':other}).status_code==409
            assert c.post(f'/api/accounts/{b}/holders',json={'username':other}).status_code==200
            assert any(x['id']==b and x['holder_count']==2 for x in d.get('/api/accounts').json())
            assert c.get('/api/recipients',params={'q':other+'@test.dev'}).json()[0]['username']==other
            before=c.get('/api/insights').json()['monthly']
            body={'source_account_id':a,'destination_account_id':dest,'amount_cents':1234,'memo':'=1+1','idempotency_key':str(uuid4())}
            r=c.post('/api/transfers',json=body);assert r.status_code==201,r.text
            assert c.post('/api/transfers',json=body).json()['id']==r.json()['id']
            assert d.post('/api/transfers',json={**body,'idempotency_key':str(uuid4())}).status_code==409
            assert c.post('/api/transfers',json={**body,'destination_account_id':b,'amount_cents':100,'idempotency_key':str(uuid4())}).status_code==201
            monthly=c.get('/api/insights').json()['monthly']
            assert monthly['sent_cents']-before['sent_cents']==1234
            assert monthly['received_cents']==before['received_cents']
            assert monthly['transfer_count']-before['transfer_count']==2
            rows=c.get('/api/transfers').json()
            assert len(rows)==2 and {x['direction'] for x in rows}=={'sent','internal'}
            export=list(csv.DictReader(io.StringIO(c.get('/api/activity.csv').text)))
            assert len(export)==2 and all(x['memo']=="'=1+1" for x in export)
            assert c.post('/api/auth/logout').status_code==200
            assert c.post('/api/auth/login',json={'username':name+'@test.dev','password':'Test!workflow2026'}).status_code==200
    finally:
        with psycopg.connect(C['ADMIN_DATABASE_URL']) as conn:
            conn.execute('DELETE FROM paylink.transfers WHERE initiated_by=ANY(%s::uuid[])',(ids,))
            conn.execute('DELETE FROM paylink.account_holders WHERE user_id=ANY(%s::uuid[])',(ids,))
            conn.execute('DELETE FROM paylink.bank_accounts WHERE id=ANY(%s::uuid[])',(account_ids,))
            conn.execute('DELETE FROM paylink.users WHERE id=ANY(%s::uuid[])',(ids,))
