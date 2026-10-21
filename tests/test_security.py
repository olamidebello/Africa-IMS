import os,tempfile,unittest,io
os.environ['AIMS_DATA']=tempfile.mkdtemp();os.environ['AIMS_SECURE']='0'
from app import app,db,init,generate_password_hash
class PlatformTests(unittest.TestCase):
 def setUp(self):
  app.config['TESTING']=True;app.config['ATTEMPTS']={}
  with db() as c:
   for table in ['audit','documents','applications','appointments','messages','resets','users','tenants']:c.execute('DELETE FROM '+table)
   c.executemany('INSERT INTO tenants(id,name) VALUES(?,?)',[(1,'One'),(2,'Two')])
   for id,tenant,role in [(1,1,'user'),(2,1,'staff'),(3,2,'user'),(4,1,'super_admin')]:c.execute('INSERT INTO users(id,tenant,name,email,password,role) VALUES(?,?,?,?,?,?)',(id,tenant,role,str(id)+'@test.org',generate_password_hash('strongpassword12'),role))
  self.client=app.test_client();self.login(1)
 def login(self,id):
  r=self.client.post('/api/login',json={'email':str(id)+'@test.org','password':'strongpassword12'});self.assertEqual(r.status_code,200)
  self.csrf=self.client.get('/api/me').json['csrf']
 def post(self,path,data):return self.client.post('/api/'+path,json=data,headers={'X-CSRF-Token':self.csrf})
 def patch(self,path,data):return self.client.patch('/api/'+path,json=data,headers={'X-CSRF-Token':self.csrf})
 def test_tenant_isolation(self):
  id=self.post('applications',{'service':'birth','data':{}}).json['id'];self.login(3)
  self.assertEqual(self.client.get('/api/applications').json,[])
  self.assertEqual(self.client.get('/api/applications/'+str(id)).status_code,404)
  self.assertEqual(self.patch('applications/'+str(id),{'status':'under_review'}).status_code,404)
 def test_role_and_csrf(self):
  self.assertEqual(self.client.get('/api/users').status_code,403)
  self.assertEqual(self.client.post('/api/applications',json={'service':'birth'}).status_code,403)
  self.assertEqual(self.post('tenants',{'name':'Evil'}).status_code,403)
 def test_workflow(self):
  from app import SERVICES
  data={f:'Example' for f in next(s for s in SERVICES if s['id']=='birth')['fields']}
  id=self.post('applications',{'service':'birth','data':data}).json['id']
  self.assertEqual(self.patch('applications/'+str(id),{'status':'approved_for_handoff'}).status_code,400)
  self.assertEqual(self.patch('applications/'+str(id),{'status':'submitted'}).status_code,200)
  self.assertEqual(self.patch('applications/'+str(id),{'status':'under_review'}).status_code,403)
  self.login(2)
  self.assertEqual(self.patch('applications/'+str(id),{'status':'under_review'}).status_code,200)
  self.assertEqual(self.patch('applications/'+str(id),{'status':'denied'}).status_code,400)
  self.assertEqual(self.patch('applications/'+str(id),{'status':'approved_for_handoff'}).status_code,200)
 def test_upload_access(self):
  id=self.post('applications',{'service':'birth'}).json['id']
  r=self.client.post('/api/applications/'+str(id)+'/documents',data={'file':(io.BytesIO(b'%PDF-1.4\nfixture'),'evidence.pdf')},headers={'X-CSRF-Token':self.csrf});self.assertEqual(r.status_code,201)
  doc=self.client.get('/api/applications/'+str(id)).json['documents'][0]['id']
  self.login(3);self.assertEqual(self.client.get('/api/documents/'+str(doc)).status_code,404)
 def test_tenant_switch(self):
  self.login(4);self.assertEqual(self.post('tenant-switch',{'tenant':2}).status_code,200)
  self.assertEqual(self.client.get('/api/me').json['tenant'],2)
 def test_assets_and_home(self):
  self.assertEqual(self.client.get('/').status_code,200)
  with self.client.get('/static/logo.png') as r:self.assertEqual(r.status_code,200)
  self.assertEqual(self.client.get('/api/health').json['status'],'ok')
if __name__=='__main__':unittest.main()
