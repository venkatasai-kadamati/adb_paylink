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
