import os, sqlite3, secrets, hashlib, json, datetime, functools, pathlib, mimetypes
from flask import Flask, request, session, jsonify, send_from_directory, render_template
from werkzeug.security import generate_password_hash, check_password_hash

ROOT=pathlib.Path(__file__).parent
DATA=pathlib.Path(os.getenv('AIMS_DATA', str(ROOT/'var')))
DATA.mkdir(mode=0o700,parents=True,exist_ok=True)
(DATA/'uploads').mkdir(mode=0o700,exist_ok=True)
keyfile=DATA/'session.key'
if not keyfile.exists():
    fd=os.open(keyfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(secrets.token_hex(32))
app=Flask(__name__)
app.config.update(SECRET_KEY=keyfile.read_text(),MAX_CONTENT_LENGTH=10*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('AIMS_SECURE','1')=='1',PERMANENT_SESSION_LIFETIME=datetime.timedelta(hours=8))

def db():
    c=sqlite3.connect(DATA/'aims.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c

def init():
    with db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS tenants(id INTEGER PRIMARY KEY,name TEXT NOT NULL,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,tenant INTEGER REFERENCES tenants(id),name TEXT,email TEXT UNIQUE,password TEXT,role TEXT DEFAULT 'user',active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY,tenant INTEGER REFERENCES tenants(id),owner INTEGER REFERENCES users(id),service TEXT,data TEXT,status TEXT DEFAULT 'draft',assigned INTEGER REFERENCES users(id),reason TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP,updated TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,tenant INTEGER,owner INTEGER,application INTEGER REFERENCES applications(id),name TEXT,path TEXT,mime TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY,tenant INTEGER,owner INTEGER,service TEXT,scheduled TEXT,status TEXT DEFAULT 'requested');
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,tenant INTEGER,owner INTEGER,body TEXT,reply TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,tenant INTEGER,actor INTEGER,action TEXT,entity TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS resets(token TEXT PRIMARY KEY,user INTEGER,expires REAL);
INSERT OR IGNORE INTO tenants(id,name) VALUES(1,'AIMS Community');
''')
init()
REGIONS=json.loads((ROOT/'static/regions.json').read_text())
with db() as c:
 columns={r['name'] for r in c.execute('PRAGMA table_info(users)')}
 for col,default in [('language','pcm'),('currency','AFR')]:
  if col not in columns:c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT '{default}'")
SERVICES=[{'id':x,'name':n,'category':cat,'fields':fields} for x,n,cat,fields in [
('identity','Identity enrollment','Identity',['Full legal name','Previous names','Date of birth','Place of birth','Nationality','Residential address','Phone']),
('ssn','SS-5 preparation','Social protection',['Full legal name','Name at birth','Date of birth','Place of birth','Citizenship status','Parent names','Mailing address','Request type']),
('benefits','Benefit application support','Social protection',['Full legal name','Date of birth','Benefit type','Employment history','Household details','Income summary']),
('citizenship','Citizenship / naturalization intake','Citizenship',['Full legal name','Date of birth','Nationality','Residence history','Employment history','Travel history','Marital history','Eligibility basis']),
('birth','Birth registration intake','Life events',['Child name','Date of birth','Time of birth','Place of birth','Parent names','Parent contact','Facility or attendant']),
('marriage','Marriage registration intake','Life events',['First applicant name','Second applicant name','Applicant birth dates','Residential address','Prior marriage history','Ceremony date','Officiant']),
('death','Death registration intake','Life events',['Decedent name','Date of birth','Date of death','Place of death','Informant name','Informant relationship','Certifier contact']),
('passport','Passport application support','Identity',['Full legal name','Date of birth','Place of birth','Nationality','Mailing address','Parent names','Application type']),
('correction','Record correction','Records',['Record reference','Record type','Current entry','Requested correction','Reason']),
('copies','Record-copy request','Records',['Record reference','Record type','Requester relationship','Purpose','Delivery address']),
('appeal','Decision review request','Records',['Application reference','Decision date','Reasons for review','Additional evidence summary'])]]

def audit(c,u,action,entity):c.execute('INSERT INTO audit(tenant,actor,action,entity) VALUES(?,?,?,?)',(u['tenant'],u['id'],action,str(entity)))
def error(message,status=400):return jsonify(error=message),status

def auth(roles=None):
 def deco(fn):
  @functools.wraps(fn)
  def wrapped(*args,**kwargs):
   with db() as c:u=c.execute('SELECT u.* FROM users u JOIN tenants t ON t.id=u.tenant WHERE u.id=? AND u.active=1 AND t.active=1',(session.get('uid'),)).fetchone()
   if not u:return error('Please sign in.',401)
   if roles and u['role'] not in roles:return error('Permission denied.',403)
   if request.method not in ('GET','HEAD') and not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','!')):return error('Invalid security token.',403)
   return fn(dict(u),*args,**kwargs)
  return wrapped
 return deco

def accessible(c,u,id):
 a=c.execute('SELECT * FROM applications WHERE id=? AND tenant=?',(id,u['tenant'])).fetchone()
 return a if a and (u['role']!='user' or a['owner']==u['id']) else None

@app.after_request
def headers(r):
 r.headers['X-Content-Type-Options']='nosniff';r.headers['X-Frame-Options']='DENY';r.headers['Referrer-Policy']='same-origin';r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
 if request.path.startswith('/api/'):r.headers['Cache-Control']='no-store'
 return r
@app.errorhandler(413)
def large(e):return error('File exceeds the 10 MB limit.',413)
@app.route('/')
def index():return render_template('index.html')
@app.get('/api/health')
def health():
 with db() as c:c.execute('SELECT 1').fetchone()
 return jsonify(status='ok',name='AIMS')
@app.get('/api/services')
def services():return jsonify(SERVICES)
@app.get('/api/tenants/public')
def public_tenants():
 with db() as c:return jsonify([dict(r) for r in c.execute('SELECT id,name FROM tenants WHERE active=1')])
@app.post('/api/register')
def register():
 d=request.get_json() or {};email=d.get('email','').strip().lower();pw=d.get('password','');name=d.get('name','').strip()
 if '@' not in email or len(pw)<12 or not name:return error('Enter your name, valid email and a password of at least 12 characters.')
 if not d.get('consent'):return error('Accept the terms and privacy policy to continue.')
 try:
  with db() as c:
   t=c.execute('SELECT id FROM tenants WHERE id=? AND active=1',(d.get('tenant',1),)).fetchone()
   if not t:return error('Tenant unavailable.')
   c.execute('INSERT INTO users(tenant,name,email,password) VALUES(?,?,?,?)',(t['id'],name,email,generate_password_hash(pw)))
 except sqlite3.IntegrityError:return error('Account could not be created. Try signing in or recovering access.')
 return jsonify(ok=True),201
@app.post('/api/login')
def login():
 d=request.get_json() or {}
 # Bounded in-memory throttling; production reverse proxy also limits login requests.
 ip=request.remote_addr;now=datetime.datetime.now().timestamp();attempts=app.config.setdefault('ATTEMPTS',{});xs=[t for t in attempts.get(ip,[]) if t>now-300]
 if len(xs)>=10:return error('Too many attempts. Try again in five minutes.',429)
 attempts[ip]=xs+[now]
 with db() as c:u=c.execute('SELECT u.* FROM users u JOIN tenants t ON t.id=u.tenant WHERE email=? AND u.active=1 AND t.active=1',(d.get('email','').strip().lower(),)).fetchone()
 if not u or not check_password_hash(u['password'],d.get('password','')):return error('Invalid email or password.',401)
 attempts.pop(ip,None);session.clear();session['uid']=u['id'];session['csrf']=secrets.token_hex(32);session.permanent=True
 return jsonify(ok=True)
@app.get('/api/me')
@auth()
def me(u):
 with db() as c:t=c.execute('SELECT name FROM tenants WHERE id=?',(u['tenant'],)).fetchone()
 return jsonify(id=u['id'],name=u['name'],email=u['email'],role=u['role'],tenant=u['tenant'],tenant_name=t['name'],csrf=session['csrf'],language=u['language'],currency=u['currency'])
@app.route('/api/preferences',methods=['GET','PATCH'])
@auth()
def preferences(u):
 if request.method=='GET':return jsonify(language=u['language'],currency=u['currency'])
 d=request.get_json() or {}
 language=d.get('language',u['language']);currency=d.get('currency',u['currency'])
 if language not in {r['code'] for r in REGIONS['languages']}:return error('Choose a language from the catalog.')
 if currency not in {r['code'] for r in REGIONS['currencies']}:return error('Choose a currency from the catalog.')
 with db() as c:
  c.execute('UPDATE users SET language=?,currency=? WHERE id=?',(language,currency,u['id']))
  audit(c,u,'preferences_updated',u['id'])
 return jsonify(language=language,currency=currency)
@app.post('/api/logout')
@auth()
def logout(u):session.clear();return jsonify(ok=True)
@app.post('/api/password')
@auth()
def password(u):
 d=request.get_json() or {}
 if not check_password_hash(u['password'],d.get('current','')) or len(d.get('password',''))<12:return error('Check current password and use at least 12 characters for the new password.')
 with db() as c:c.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(d['password']),u['id']));audit(c,u,'password_changed',u['id'])
 return jsonify(ok=True)
@app.route('/api/applications',methods=['GET','POST'])
@auth()
def applications(u):
 with db() as c:
  if request.method=='GET':
   sql='SELECT a.*,u.name AS applicant FROM applications a JOIN users u ON u.id=a.owner WHERE a.tenant=?';args=[u['tenant']]
   if u['role']=='user':sql+=' AND a.owner=?';args.append(u['id'])
   return jsonify([dict(r) for r in c.execute(sql+' ORDER BY a.id DESC',args)])
  d=request.get_json() or {}
  if d.get('service') not in [s['id'] for s in SERVICES]:return error('Choose a service.')
  cur=c.execute('INSERT INTO applications(tenant,owner,service,data) VALUES(?,?,?,?)',(u['tenant'],u['id'],d['service'],json.dumps(d.get('data',{}))))
  audit(c,u,'application_created',cur.lastrowid);return jsonify(id=cur.lastrowid),201
@app.route('/api/applications/<int:id>',methods=['GET','PATCH'])
@auth()
def application(u,id):
 with db() as c:
  a=accessible(c,u,id)
  if not a:return error('Application not found.',404)
  if request.method=='GET':
   return jsonify(application=dict(a),documents=[dict(r) for r in c.execute('SELECT id,name,mime,created FROM documents WHERE application=?',(id,))],timeline=[dict(r) for r in c.execute('SELECT action,created FROM audit WHERE tenant=? AND entity=? ORDER BY id',(u['tenant'],str(id)))])
  d=request.get_json() or {};status=d.get('status',a['status']);reason=d.get('reason',a['reason']);assigned=d.get('assigned',a['assigned'])
  transitions={'draft':['submitted'],'submitted':['under_review','returned'],'under_review':['evidence_requested','approved_for_handoff','denied','returned'],'evidence_requested':['submitted'],'returned':['submitted']}
  if status!=a['status']:
   if status not in transitions.get(a['status'],[]):return error('Invalid status transition.')
   if u['role']=='user' and status!='submitted':return error('Staff review required.',403)
   if status in ['denied','returned','evidence_requested'] and not reason:return error('A reason is required.')
  if assigned!=a['assigned']:
   if u['role']=='user':return error('Staff permission required.',403)
   if assigned and not c.execute("SELECT id FROM users WHERE id=? AND tenant=? AND role IN ('staff','tenant_admin','super_admin')",(assigned,u['tenant'])).fetchone():return error('Choose staff from this tenant.')
  payload=a['data']
  if 'data' in d:
   if a['owner']!=u['id'] or a['status'] not in ['draft','returned','evidence_requested']:return error('This application cannot be edited.',403)
   payload=json.dumps(d['data'])
  if status=='submitted':
   fields=next(s['fields'] for s in SERVICES if s['id']==a['service'])
   values=json.loads(payload)
   if any(not str(values.get(f,'')).strip() for f in fields):return error('Complete all required fields before submission.')
  if u['role']=='user':reason=a['reason']
  c.execute('UPDATE applications SET data=?,status=?,reason=?,assigned=?,updated=CURRENT_TIMESTAMP WHERE id=?',(payload,status,reason,assigned,id));audit(c,u,'application_'+status,id)
 return jsonify(ok=True)
@app.post('/api/applications/<int:id>/documents')
@auth()
def upload(u,id):
 with db() as c:
  a=accessible(c,u,id)
  if not a or a['owner']!=u['id']:return error('Application not found.',404)
  if a['status'] not in ['draft','returned','evidence_requested']:return error('Uploads are closed for this status.')
  f=request.files.get('file')
  if not f:return error('Choose a file.')
  name=pathlib.Path(f.filename).name;ext=pathlib.Path(name).suffix.lower()
  if ext not in ['.pdf','.png','.jpg','.jpeg']:return error('Use PDF, PNG or JPEG.')
  raw=f.read();valid=(ext=='.pdf' and raw.startswith(b'%PDF-')) or (ext=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in ['.jpg','.jpeg'] and raw.startswith(b'\xff\xd8\xff'))
  if not valid:return error('File contents do not match its type.')
  path=secrets.token_hex(24)+ext;(DATA/'uploads'/path).write_bytes(raw);os.chmod(DATA/'uploads'/path,0o600)
  c.execute('INSERT INTO documents(tenant,owner,application,name,path,mime) VALUES(?,?,?,?,?,?)',(u['tenant'],u['id'],id,name,path,mimetypes.guess_type(name)[0]));audit(c,u,'document_uploaded',id)
 return jsonify(ok=True),201
@app.get('/api/documents/<int:id>')
@auth()
def download(u,id):
 with db() as c:
  d=c.execute('SELECT * FROM documents WHERE id=? AND tenant=?',(id,u['tenant'])).fetchone()
  if not d or (u['role']=='user' and d['owner']!=u['id']):return error('Document not found.',404)
  audit(c,u,'document_downloaded',d['application'])
 return send_from_directory(DATA/'uploads',d['path'],as_attachment=True,download_name=d['name'])
@app.route('/api/appointments',methods=['GET','POST'])
@auth()
def appointments(u):
 with db() as c:
  if request.method=='POST':
   d=request.get_json() or {}
   try:dt=datetime.datetime.fromisoformat(d['scheduled']);assert dt>datetime.datetime.now()
   except (KeyError,ValueError,AssertionError):return error('Choose a future appointment time (server local time).')
   if d.get('service') not in [s['id'] for s in SERVICES]:return error('Invalid service.')
   c.execute('INSERT INTO appointments(tenant,owner,service,scheduled) VALUES(?,?,?,?)',(u['tenant'],u['id'],d['service'],d['scheduled']));audit(c,u,'appointment_requested','appointment');return jsonify(ok=True),201
  sql='SELECT a.*,u.name AS applicant FROM appointments a JOIN users u ON a.owner=u.id WHERE a.tenant=?';args=[u['tenant']]
  if u['role']=='user':sql+=' AND owner=?';args.append(u['id'])
  return jsonify([dict(r) for r in c.execute(sql+' ORDER BY scheduled',args)])
@app.patch('/api/appointments/<int:id>')
@auth()
def appointment_update(u,id):
 with db() as c:
  a=c.execute('SELECT * FROM appointments WHERE id=? AND tenant=?',(id,u['tenant'])).fetchone();status=(request.get_json() or {}).get('status')
  if not a or (u['role']=='user' and a['owner']!=u['id']):return error('Not found.',404)
  if status not in (['cancelled'] if u['role']=='user' else ['confirmed','cancelled','completed']):return error('Invalid status.')
  c.execute('UPDATE appointments SET status=? WHERE id=?',(status,id));audit(c,u,'appointment_'+status,id)
 return jsonify(ok=True)
@app.route('/api/messages',methods=['GET','POST'])
@auth()
def messages(u):
 with db() as c:
  if request.method=='POST':
   body=(request.get_json() or {}).get('body','').strip()
   if not body or len(body)>5000:return error('Enter a message up to 5000 characters.')
   c.execute('INSERT INTO messages(tenant,owner,body) VALUES(?,?,?)',(u['tenant'],u['id'],body));return jsonify(ok=True),201
  sql='SELECT m.*,u.name AS applicant FROM messages m JOIN users u ON m.owner=u.id WHERE m.tenant=?';args=[u['tenant']]
  if u['role']=='user':sql+=' AND owner=?';args.append(u['id'])
  return jsonify([dict(r) for r in c.execute(sql+' ORDER BY m.id DESC',args)])
@app.patch('/api/messages/<int:id>')
@auth(['staff','tenant_admin','super_admin'])
def reply(u,id):
 body=(request.get_json() or {}).get('reply','').strip()
 if not body:return error('Enter a reply.')
 with db() as c:
  cur=c.execute('UPDATE messages SET reply=? WHERE id=? AND tenant=?',(body,id,u['tenant']))
  if not cur.rowcount:return error('Not found.',404)
  audit(c,u,'message_replied',id)
 return jsonify(ok=True)
@app.route('/api/users',methods=['GET','POST'])
@auth(['tenant_admin','super_admin'])
def users(u):
 with db() as c:
  if request.method=='GET':return jsonify([dict(r) for r in c.execute('SELECT id,name,email,role,active FROM users WHERE tenant=?',(u['tenant'],))])
  d=request.get_json() or {};role=d.get('role','user')
  if role not in ['user','staff','tenant_admin']:return error('Invalid role.')
  if len(d.get('password',''))<12 or not d.get('name') or '@' not in d.get('email',''):return error('Name, email and a 12-character password are required.')
  try:c.execute('INSERT INTO users(tenant,name,email,password,role) VALUES(?,?,?,?,?)',(u['tenant'],d['name'],d['email'].strip().lower(),generate_password_hash(d['password']),role));audit(c,u,'user_created',d['email'])
  except sqlite3.IntegrityError:return error('Email already registered.')
 return jsonify(ok=True),201
@app.patch('/api/users/<int:id>')
@auth(['tenant_admin','super_admin'])
def user_update(u,id):
 d=request.get_json() or {}
 with db() as c:
  target=c.execute('SELECT * FROM users WHERE id=? AND tenant=?',(id,u['tenant'])).fetchone()
  if not target or target['role']=='super_admin' or id==u['id']:return error('Account cannot be modified here.',403)
  role=d.get('role',target['role']);active=int(bool(d.get('active',target['active'])))
  if role not in ['user','staff','tenant_admin']:return error('Invalid role.')
  c.execute('UPDATE users SET role=?,active=? WHERE id=?',(role,active,id));audit(c,u,'user_updated',id)
 return jsonify(ok=True)
@app.route('/api/tenants',methods=['GET','POST'])
@auth(['super_admin'])
def tenants(u):
 with db() as c:
  if request.method=='GET':return jsonify([dict(r) for r in c.execute('SELECT * FROM tenants')])
  name=(request.get_json() or {}).get('name','').strip()
  if not name:return error('Tenant name required.')
  cur=c.execute('INSERT INTO tenants(name) VALUES(?)',(name,));audit(c,u,'tenant_created',cur.lastrowid)
 return jsonify(ok=True),201
@app.post('/api/tenant-switch')
@auth(['super_admin'])
def switch(u):
 id=(request.get_json() or {}).get('tenant')
 with db() as c:
  if not c.execute('SELECT id FROM tenants WHERE id=? AND active=1',(id,)).fetchone():return error('Tenant unavailable.')
  audit(c,u,'tenant_switched',id);c.execute('UPDATE users SET tenant=? WHERE id=?',(id,u['id']))
 return jsonify(ok=True)
@app.get('/api/audit')
@auth(['tenant_admin','super_admin'])
def audits(u):
 with db() as c:return jsonify([dict(r) for r in c.execute('SELECT * FROM audit WHERE tenant=? ORDER BY id DESC LIMIT 500',(u['tenant'],))])
@app.get('/install')
def install_page():return render_template('install.html')
@app.get('/download')
def apk():
 p=ROOT/'static/downloads/AIMS.apk'
 if not p.exists():return error('Android release is not published yet. Install the web app from your browser menu.',503)
 return send_from_directory(p.parent,p.name,as_attachment=True)
if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.getenv('PORT','18840')))
