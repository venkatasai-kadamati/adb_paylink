from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID
import csv
import io
import os
import time
from collections import defaultdict, deque

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from psycopg import errors
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(os.getenv('PAYLINK_ENV_FILE', str(ROOT / '.env')))
SECRET = os.environ['JWT_SECRET']
if len(SECRET) < 32:
    raise RuntimeError('JWT_SECRET must be at least 32 characters')
ph = PasswordHasher()
DUMMY_HASH = ph.hash('not-a-real-user-password')
pool: ConnectionPool

@asynccontextmanager
async def lifespan(app):
    global pool
    pool = ConnectionPool(os.environ['DATABASE_URL'], min_size=1, max_size=8, open=False,
                          kwargs={'row_factory': dict_row,
                                  'options': '-c statement_timeout=10000 -c timezone=America/Chicago'})
    pool.open(wait=True)
    yield
    pool.close()

app = FastAPI(title='PayLink API', version='1.0.0', lifespan=lifespan)

@app.middleware('http')
async def security_headers(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        allowed = os.getenv('APP_ORIGIN', 'http://localhost:3000')
        if origin and origin != allowed:
            return Response('Origin not permitted', status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return Response('Cross-site request not permitted', status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response

attempts = defaultdict(deque)
def rate_limit(request: Request):
    # In-process limiter for this single-worker teaching deployment.
    key = request.client.host if request.client else 'local'
    now = time.monotonic()
    q = attempts[key]
    while q and now-q[0] > 60:
        q.popleft()
    if len(q) >= 20:
        raise HTTPException(429, 'Too many attempts. Try again in a minute.')
    q.append(now)

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)

class Register(BaseModel):
    username: str = Field(pattern=r'^[a-z][a-z0-9_]{2,29}$')
    email: str = Field(max_length=254, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    phone: str | None = Field(default=None, pattern=r'^\+[1-9][0-9]{7,14}$')
    full_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=10, max_length=128)
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v): return v.lower().strip()
    @field_validator('full_name')
    @classmethod
    def clean_name(cls, v):
        if not v.strip(): raise ValueError('Name cannot be empty')
        return v.strip()

class AccountCreate(BaseModel):
    bank_id: UUID
    account_type: Literal['checking','savings']
    label: str = Field(min_length=1, max_length=60)

class HolderCreate(BaseModel):
    username: str = Field(pattern=r'^[a-z][a-z0-9_]{2,29}$')

class TransferCreate(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount_cents: int = Field(strict=True, ge=1, le=100000000)
    memo: str = Field(default='', max_length=140)
    idempotency_key: UUID

def current_user(request: Request):
    try:
        token = request.cookies.get('paylink_session', '')
        payload = jwt.decode(token, SECRET, algorithms=['HS256'], audience='paylink', issuer='paylink-api',
                             options={'require': ['exp','sub','iat','aud','iss']})
        uid = UUID(payload['sub'])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Sign in to continue')
    with pool.connection() as conn:
        user = conn.execute('SELECT id,username,email,phone,full_name FROM paylink.users WHERE id=%s', (uid,)).fetchone()
    if not user: raise HTTPException(401, 'Sign in to continue')
    return user
User = Annotated[dict, Depends(current_user)]

def session(response, uid):
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub': str(uid), 'iat': now, 'exp': now+timedelta(hours=8),
                        'aud':'paylink','iss':'paylink-api'}, SECRET, algorithm='HS256')
    response.set_cookie('paylink_session', token, httponly=True, samesite='strict', max_age=28800,
                        secure=os.getenv('COOKIE_SECURE','false').lower()=='true', path='/')

@app.get('/api/health')
def health():
    with pool.connection() as c: c.execute('SELECT 1').fetchone()
    return {'status':'ok','database':'connected','simulation':True}

@app.post('/api/auth/register', status_code=201, dependencies=[Depends(rate_limit)])
def register(body: Register, response: Response):
    hashed = ph.hash(body.password)
    try:
        with pool.connection() as c:
            row = c.execute('''INSERT INTO paylink.users(username,email,phone,full_name,password_hash)
                VALUES(%s,%s,%s,%s,%s) RETURNING id,username,full_name''',
                (body.username,body.email,body.phone,body.full_name,hashed)).fetchone()
    except errors.UniqueViolation:
        raise HTTPException(409,'Username, email, or phone already registered')
    session(response,row['id'])
    return row

@app.post('/api/auth/login', dependencies=[Depends(rate_limit)])
def login(body: Login, response: Response):
    with pool.connection() as c:
        row = c.execute('SELECT * FROM paylink.users WHERE username=%s OR email=%s',
                        (body.username.lower().strip(),body.username.lower().strip())).fetchone()
    try: ph.verify(row['password_hash'] if row else DUMMY_HASH, body.password)
    except VerificationError: raise HTTPException(401,'Incorrect username or password')
    if not row: raise HTTPException(401,'Incorrect username or password')
    session(response,row['id'])
    return {'id':row['id'],'username':row['username'],'full_name':row['full_name']}

@app.post('/api/auth/logout')
def logout(response: Response):
    response.delete_cookie('paylink_session',path='/')
    return {'ok':True}

@app.get('/api/me')
def me(user: User): return user

ACCOUNT_SQL = '''SELECT a.id,a.label,a.account_type,a.balance_cents,a.active,
    right(a.account_number,4) AS last4,b.name AS bank_name,
    (SELECT count(*) FROM paylink.account_holders h2 WHERE h2.account_id=a.id) AS holder_count
    FROM paylink.bank_accounts a JOIN paylink.banks b ON b.id=a.bank_id
    JOIN paylink.account_holders h ON h.account_id=a.id WHERE h.user_id=%s ORDER BY a.created_at,a.id'''

@app.get('/api/accounts')
def accounts(user: User):
    with pool.connection() as c: return c.execute(ACCOUNT_SQL,(user['id'],)).fetchall()

@app.get('/api/banks')
def banks(user: User):
    with pool.connection() as c: return c.execute('SELECT id,name FROM paylink.banks ORDER BY name').fetchall()

@app.post('/api/accounts',status_code=201)
def open_account(body:AccountCreate,user:User):
    try:
        with pool.connection() as c:
            result = c.execute('SELECT paylink.open_account(%s,%s,%s,%s) AS id',
                                (user['id'],body.bank_id,body.account_type,body.label.strip())).fetchone()
        return result
    except (errors.RaiseException,errors.CheckViolation,errors.ForeignKeyViolation) as e:
        raise HTTPException(400, e.diag.message_primary if isinstance(e,errors.RaiseException) else 'Invalid account details')

@app.get('/api/recipients')
def recipients(user:User,q:str=''):
    if len(q.strip())<2: return []
    # Exact matching avoids exposing a public customer directory.
    with pool.connection() as c:
        return c.execute('''SELECT u.id,u.username,u.full_name,a.id AS account_id,b.name AS bank_name,
          right(a.account_number,4) AS last4 FROM paylink.users u
          JOIN paylink.account_holders h ON h.user_id=u.id JOIN paylink.bank_accounts a ON a.id=h.account_id
          JOIN paylink.banks b ON b.id=a.bank_id
          WHERE (u.username=%s OR u.email=%s OR u.phone=%s) AND u.id<>%s AND a.active
          ORDER BY a.created_at LIMIT 8''',(q.lower().strip(),q.lower().strip(),q.strip(),user['id'])).fetchall()

@app.post('/api/accounts/{account_id}/holders')
def add_holder(account_id: UUID, body: HolderCreate, user: User):
    try:
        with pool.connection() as c:
            result = c.execute('SELECT paylink.add_account_holder(%s,%s,%s) AS user_id',
                               (user['id'], account_id, body.username)).fetchone()
        return result
    except errors.RaiseException as e:
        raise HTTPException(409, e.diag.message_primary)

@app.post('/api/transfers',status_code=201)
def send(body:TransferCreate,user:User):
    try:
        with pool.connection() as c:
            return c.execute('SELECT * FROM paylink.execute_transfer(%s,%s,%s,%s,%s,%s)',
                (user['id'],body.source_account_id,body.destination_account_id,body.amount_cents,body.memo,body.idempotency_key)).fetchone()
    except errors.RaiseException as e: raise HTTPException(409,e.diag.message_primary)
    except errors.CheckViolation: raise HTTPException(409,'Transfer exceeds an account limit')

HISTORY_SQL = '''WITH mine AS (SELECT account_id FROM paylink.account_holders WHERE user_id=%s)
 SELECT t.id,t.amount_cents,t.memo,t.created_at,t.source_account_id,t.destination_account_id,
 CASE WHEN t.source_account_id IN(SELECT account_id FROM mine) AND t.destination_account_id IN(SELECT account_id FROM mine)
 THEN 'internal' WHEN t.source_account_id IN(SELECT account_id FROM mine) THEN 'sent' ELSE 'received' END AS direction,
 s.label AS source_label,d.label AS destination_label,
 COALESCE((SELECT u.full_name FROM paylink.account_holders h JOIN paylink.users u ON u.id=h.user_id
 WHERE h.account_id=CASE WHEN t.source_account_id IN(SELECT account_id FROM mine)
 THEN t.destination_account_id ELSE t.source_account_id END ORDER BY h.joined_at,u.id LIMIT 1),'Account') AS counterparty
 FROM paylink.transfers t JOIN paylink.bank_accounts s ON s.id=t.source_account_id
 JOIN paylink.bank_accounts d ON d.id=t.destination_account_id
 WHERE t.source_account_id IN(SELECT account_id FROM mine) OR t.destination_account_id IN(SELECT account_id FROM mine)
 ORDER BY t.created_at DESC,t.id DESC LIMIT 200'''
@app.get('/api/transfers')
def history(user:User):
    with pool.connection() as c: return c.execute(HISTORY_SQL,(user['id'],)).fetchall()

@app.get('/api/activity.csv')
def export(user:User):
    rows=history(user)
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(['id','date','direction','amount_usd','counterparty','memo'])
    def safe(v):
        s=str(v)
        return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s
    for r in rows:
        writer.writerow([r['id'],r['created_at'],r['direction'],f"{r['amount_cents']//100}.{r['amount_cents']%100:02d}",safe(r['counterparty']),safe(r['memo'])])
    return StreamingResponse(iter([output.getvalue()]),media_type='text/csv',
        headers={'Content-Disposition':'attachment; filename="paylink-activity.csv"'})

@app.get('/api/insights')
def insights(user:User):
    with pool.connection() as c:
        monthly=c.execute('''WITH mine AS(SELECT account_id FROM paylink.account_holders WHERE user_id=%s)
          SELECT count(*) AS transfer_count,
          coalesce(sum(amount_cents) FILTER(WHERE source_account_id IN(SELECT account_id FROM mine)
           AND destination_account_id NOT IN(SELECT account_id FROM mine)),0)::bigint AS sent_cents,
          coalesce(sum(amount_cents) FILTER(WHERE destination_account_id IN(SELECT account_id FROM mine)
           AND source_account_id NOT IN(SELECT account_id FROM mine)),0)::bigint AS received_cents
          FROM paylink.transfers WHERE created_at>=date_trunc('month',now())
          AND (source_account_id IN(SELECT account_id FROM mine) OR destination_account_id IN(SELECT account_id FROM mine))''',(user['id'],)).fetchone()
        weekly=c.execute('''WITH days AS(SELECT generate_series(current_date-6,current_date,'1 day')::date AS day),
          mine AS(SELECT account_id FROM paylink.account_holders WHERE user_id=%s)
          SELECT days.day,coalesce(sum(t.amount_cents) FILTER(WHERE t.source_account_id IN(SELECT account_id FROM mine)),0)::bigint AS sent,
          coalesce(sum(t.amount_cents) FILTER(WHERE t.destination_account_id IN(SELECT account_id FROM mine)),0)::bigint AS received
          FROM days LEFT JOIN paylink.transfers t ON t.created_at>=days.day AND t.created_at<days.day+interval '1 day'
          AND (t.source_account_id IN(SELECT account_id FROM mine) OR t.destination_account_id IN(SELECT account_id FROM mine))
          GROUP BY days.day ORDER BY days.day''',(user['id'],)).fetchall()
    return {'monthly':monthly,'weekly':weekly}
