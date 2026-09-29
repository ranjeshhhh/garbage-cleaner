from datetime import datetime, timedelta
from pathlib import Path
import os, hashlib, hmac, secrets, math
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from jose import jwt, JWTError

ROOT=Path(__file__).parent
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./kabadiwala.db')
engine=create_engine(DATABASE_URL,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {})
SessionLocal=sessionmaker(bind=engine,autoflush=False)
class Base(DeclarativeBase): pass
class User(Base):
 __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120)); email:Mapped[str]=mapped_column(String(200),unique=True,index=True); phone:Mapped[str]=mapped_column(String(40),default=''); role:Mapped[str]=mapped_column(String(30)); city:Mapped[str]=mapped_column(String(100),default=''); address:Mapped[str]=mapped_column(Text,default=''); lat:Mapped[Optional[float]]=mapped_column(Float,nullable=True); lon:Mapped[Optional[float]]=mapped_column(Float,nullable=True); password_hash:Mapped[str]=mapped_column(String(300)); verified:Mapped[bool]=mapped_column(default=False); status:Mapped[str]=mapped_column(String(30),default='active'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Category(Base):
 __tablename__='categories'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(80)); subcategories:Mapped[str]=mapped_column(Text); rate:Mapped[float]=mapped_column(Float); unit:Mapped[str]=mapped_column(String(20),default='kg'); description:Mapped[str]=mapped_column(Text,default='')
class Pickup(Base):
 __tablename__='pickups'; id:Mapped[int]=mapped_column(primary_key=True); code:Mapped[str]=mapped_column(String(30),unique=True); customer_id:Mapped[int]=mapped_column(ForeignKey('users.id')); collector_id:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id'),nullable=True); category:Mapped[str]=mapped_column(String(80)); subcategory:Mapped[str]=mapped_column(String(80),default=''); quantity:Mapped[float]=mapped_column(Float); unit:Mapped[str]=mapped_column(String(20),default='kg'); condition:Mapped[str]=mapped_column(String(40),default='Clean'); address:Mapped[str]=mapped_column(Text); city:Mapped[str]=mapped_column(String(100),default=''); lat:Mapped[Optional[float]]=mapped_column(Float,nullable=True); lon:Mapped[Optional[float]]=mapped_column(Float,nullable=True); date:Mapped[str]=mapped_column(String(30),default=''); time:Mapped[str]=mapped_column(String(30),default=''); status:Mapped[str]=mapped_column(String(40),default='Finding Collector'); notes:Mapped[str]=mapped_column(Text,default=''); images:Mapped[str]=mapped_column(Text,default=''); actual_weight:Mapped[Optional[float]]=mapped_column(Float,nullable=True); final_amount:Mapped[Optional[float]]=mapped_column(Float,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Batch(Base):
 __tablename__='batches'; id:Mapped[int]=mapped_column(primary_key=True); code:Mapped[str]=mapped_column(String(30),unique=True); pickup_id:Mapped[int]=mapped_column(ForeignKey('pickups.id')); category:Mapped[str]=mapped_column(String(80)); quantity:Mapped[float]=mapped_column(Float); collector_id:Mapped[int]=mapped_column(ForeignKey('users.id')); recycler_id:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id'),nullable=True); status:Mapped[str]=mapped_column(String(30),default='Listed'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Notice(Base):
 __tablename__='notifications'; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); message:Mapped[str]=mapped_column(Text); read:Mapped[bool]=mapped_column(default=False); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Complaint(Base):
 __tablename__='complaints'; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); pickup_code:Mapped[str]=mapped_column(String(30),default=''); category:Mapped[str]=mapped_column(String(80)); description:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(30),default='Open'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
Base.metadata.create_all(engine)
def get_db():
 db=SessionLocal()
 try: yield db
 finally: db.close()
def pw_hash(p):
 salt=secrets.token_hex(16); return salt+':'+hashlib.scrypt(p.encode(),salt=bytes.fromhex(salt),n=2**14,r=8,p=1).hex()
def verify(p,h):
 try: salt,digest=h.split(':'); return hmac.compare_digest(hashlib.scrypt(p.encode(),salt=bytes.fromhex(salt),n=2**14,r=8,p=1).hex(),digest)
 except: return False
SECRET=os.getenv('JWT_SECRET','local-development-secret-change-this')
security=HTTPBearer(auto_error=False)
def current_user(creds:HTTPAuthorizationCredentials=Depends(security),db:Session=Depends(get_db)):
 if not creds: raise HTTPException(401,'Please sign in to continue.')
 try: uid=jwt.decode(creds.credentials,SECRET,algorithms=['HS256'])['sub']
 except JWTError: raise HTTPException(401,'Your session has expired. Please sign in again.')
 u=db.get(User,int(uid))
 if not u or u.status!='active': raise HTTPException(401,'Account unavailable.')
 return u
def role(*allowed):
 def check(u:User=Depends(current_user)):
  if u.role not in allowed: raise HTTPException(403,'You do not have access to this section.')
  return u
 return check
def notify(db,uid,msg): db.add(Notice(user_id=uid,message=msg))
def user_json(u): return {'id':u.id,'name':u.name,'email':u.email,'phone':u.phone,'role':u.role,'city':u.city,'address':u.address,'verified':u.verified,'status':u.status,'lat':u.lat,'lon':u.lon}
def pickup_json(p,db,viewer=None):
 customer=db.get(User,p.customer_id); collector=db.get(User,p.collector_id) if p.collector_id else None
 distance=None
 if viewer and viewer.lat is not None and viewer.lon is not None and p.lat is not None and p.lon is not None:
  a,b=map(math.radians,[viewer.lat,p.lat]); dlon=math.radians(p.lon-viewer.lon); dlat=math.radians(p.lat-viewer.lat); x=math.sin(dlat/2)**2+math.cos(a)*math.cos(b)*math.sin(dlon/2)**2; distance=round(6371*2*math.atan2(math.sqrt(x),math.sqrt(1-x)),1)
 return {'id':p.id,'code':p.code,'customer':customer.name if customer else 'Customer','customer_phone':customer.phone if customer else '', 'collector':collector.name if collector else None,'category':p.category,'subcategory':p.subcategory,'quantity':p.quantity,'unit':p.unit,'condition':p.condition,'address':p.address,'city':p.city,'lat':p.lat,'lon':p.lon,'distance_km':distance,'date':p.date,'time':p.time,'status':p.status,'notes':p.notes,'images':[x for x in p.images.split('|') if x],'actual_weight':p.actual_weight,'final_amount':p.final_amount,'created_at':p.created_at.isoformat()}
app=FastAPI(title='Kabadiwala Connect API',version='1.0.0')
origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
UPLOAD_DIR=ROOT/'uploads'; UPLOAD_DIR.mkdir(exist_ok=True); app.mount('/uploads',StaticFiles(directory=UPLOAD_DIR),name='uploads')
@app.on_event('startup')
def seed():
 with SessionLocal() as db:
  if not db.query(Category).first():
   for name,subs,rate in [('Paper','Newspaper,Cardboard,Books,Office paper',12),('Plastic','PET bottles,Plastic containers,HDPE',8),('Metal','Iron,Aluminium,Steel,Copper',28),('E-waste','Mobile phones,Computers,Cables,Small electronics',45),('Glass','Bottles,Glass containers',2),('Other','Mixed recyclable',5)]: db.add(Category(name=name,subcategories=subs,rate=rate,description='Sorted recyclable materials'))
  admin_email=os.getenv('ADMIN_EMAIL','admin@kabadiwalaconnect.in')
  if not db.query(User).filter_by(email=admin_email).first(): db.add(User(name='Platform Admin',email=admin_email,role='admin',password_hash=pw_hash(os.getenv('ADMIN_PASSWORD','ChangeMe123!')),verified=True))
  db.commit()
class Register(BaseModel): name:str; email:EmailStr; password:str; role:str; phone:str=''; city:str=''
class Login(BaseModel): email:EmailStr; password:str
class PickupIn(BaseModel): category:str; subcategory:str=''; quantity:float; unit:str='kg'; condition:str='Clean'; address:str; city:str=''; lat:Optional[float]=None; lon:Optional[float]=None; date:str=''; time:str=''; notes:str=''; images:list[str]=[]
class CollectIn(BaseModel): actual_weight:float; quality:str='Standard'; notes:str=''
class RateIn(BaseModel): rate:float
class ComplaintIn(BaseModel): category:str; description:str; pickup_code:str=''
@app.post('/api/auth/register')
def register(x:Register,db:Session=Depends(get_db)):
 if x.role not in ['customer','collector','recycler']: raise HTTPException(400,'Choose a valid account type.')
 if len(x.password)<8: raise HTTPException(400,'Password must be at least 8 characters.')
 if db.query(User).filter_by(email=x.email.lower()).first(): raise HTTPException(409,'An account with this email already exists.')
 u=User(name=x.name,email=x.email.lower(),password_hash=pw_hash(x.password),role=x.role,phone=x.phone,city=x.city,verified=x.role=='customer'); db.add(u); db.commit(); db.refresh(u)
 if x.role!='customer':
  for a in db.query(User).filter_by(role='admin').all(): notify(db,a.id,f'New {x.role} verification request: {u.name}.')
  db.commit()
 token=jwt.encode({'sub':str(u.id),'exp':datetime.utcnow()+timedelta(days=7)},SECRET,algorithm='HS256'); return {'token':token,'user':user_json(u)}
@app.post('/api/auth/login')
def login(x:Login,db:Session=Depends(get_db)):
 u=db.query(User).filter_by(email=x.email.lower()).first()
 if not u or not verify(x.password,u.password_hash): raise HTTPException(401,'Email or password is incorrect.')
 if u.status!='active': raise HTTPException(403,'This account is suspended.')
 token=jwt.encode({'sub':str(u.id),'exp':datetime.utcnow()+timedelta(days=7)},SECRET,algorithm='HS256'); return {'token':token,'user':user_json(u)}
@app.get('/api/users/me')
def me(u:User=Depends(current_user)): return user_json(u)
@app.put('/api/users/me')
def update_me(x:dict,u:User=Depends(current_user),db:Session=Depends(get_db)):
 for k in ['name','phone','city','address','lat','lon']:
  if k in x: setattr(u,k,x[k])
 db.commit(); return user_json(u)
@app.get('/api/waste-categories')
def categories(db:Session=Depends(get_db)): return [{'id':c.id,'name':c.name,'subcategories':c.subcategories.split(','),'rate':c.rate,'unit':c.unit,'description':c.description} for c in db.query(Category).all()]
@app.post('/api/pickup-requests')
def create_pickup(x:PickupIn,u:User=Depends(role('customer')),db:Session=Depends(get_db)):
 if x.quantity<=0 or not x.address.strip(): raise HTTPException(400,'Add a valid quantity and pickup address.')
 cat=db.query(Category).filter_by(name=x.category).first()
 if not cat: raise HTTPException(400,'Choose a listed waste category.')
 p=Pickup(code='KBC-'+secrets.token_hex(4).upper(),customer_id=u.id,category=x.category,subcategory=x.subcategory,quantity=x.quantity,unit=x.unit,condition=x.condition,address=x.address,city=x.city or u.city,lat=x.lat,lon=x.lon,date=x.date,time=x.time,notes=x.notes,images='|'.join(x.images[:5]))
 db.add(p); db.commit(); db.refresh(p)
 for c in db.query(User).filter_by(role='collector',verified=True,status='active').all(): notify(db,c.id,f'New {p.category} pickup available near {p.city or "your area"}.')
 db.commit(); return pickup_json(p,db,u)
@app.get('/api/pickup-requests')
def list_pickups(status:Optional[str]=None,category:Optional[str]=None,u:User=Depends(current_user),db:Session=Depends(get_db)):
 q=db.query(Pickup)
 if u.role=='customer': q=q.filter_by(customer_id=u.id)
 elif u.role=='collector':
  q=q.filter((Pickup.collector_id==u.id)|(Pickup.status=='Finding Collector' if u.verified else Pickup.collector_id==u.id))
 elif u.role=='recycler': return []
 if status: q=q.filter_by(status=status)
 if category: q=q.filter_by(category=category)
 return [pickup_json(p,db,u) for p in q.order_by(Pickup.created_at.desc()).all()]
@app.get('/api/pickup-requests/{pid}')
def get_pickup(pid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
 p=db.get(Pickup,pid)
 if not p: raise HTTPException(404,'Pickup not found.')
 if u.role!='admin' and p.customer_id!=u.id and p.collector_id!=u.id: raise HTTPException(403,'This pickup is not available to your account.')
 return pickup_json(p,db,u)
@app.post('/api/pickup-requests/{pid}/accept')
def accept(pid:int,u:User=Depends(role('collector')),db:Session=Depends(get_db)):
 if not u.verified: raise HTTPException(403,'Your account needs admin verification before accepting pickups.')
 p=db.get(Pickup,pid)
 if not p or p.status!='Finding Collector': raise HTTPException(409,'This pickup is no longer available.')
 p.collector_id=u.id;p.status='Accepted';notify(db,p.customer_id,'Your pickup request has been accepted by a verified collector.');db.commit();return pickup_json(p,db,u)
@app.put('/api/pickup-requests/{pid}/status')
def change_status(pid:int,x:dict,u:User=Depends(current_user),db:Session=Depends(get_db)):
 p=db.get(Pickup,pid); target=x.get('status')
 transitions={'Accepted':['On The Way','Arrived','Cancelled'],'On The Way':['Arrived','Cancelled'],'Arrived':['Collected','Cancelled'],'Collected':['Completed'],'Finding Collector':['Cancelled']}
 if not p: raise HTTPException(404,'Pickup not found.')
 if u.role=='customer' and (p.customer_id!=u.id or target!='Cancelled'): raise HTTPException(403,'You cannot update this pickup.')
 if u.role=='collector' and p.collector_id!=u.id: raise HTTPException(403,'This pickup is not assigned to you.')
 if u.role not in ['customer','collector','admin'] or target not in transitions.get(p.status,[]): raise HTTPException(400,'That status update is not available.')
 p.status=target
 if target=='Cancelled' and x.get('reason'): p.notes=(p.notes+' | Cancellation: '+x['reason']).strip(' |')
 notify(db,p.customer_id,{'On The Way':'Your collector is on the way.','Arrived':'Your collector has arrived.','Collected':'Your waste has been collected.','Completed':'Your pickup is complete.'}.get(target,f'Pickup status updated: {target}.'))
 db.commit();return pickup_json(p,db,u)
@app.post('/api/pickup-requests/{pid}/collection')
def collection(pid:int,x:CollectIn,u:User=Depends(role('collector')),db:Session=Depends(get_db)):
 p=db.get(Pickup,pid)
 if not p or p.collector_id!=u.id or p.status!='Arrived': raise HTTPException(400,'Only the assigned collector can record an arrived pickup.')
 if x.actual_weight<=0: raise HTTPException(400,'Enter a valid measured weight.')
 cat=db.query(Category).filter_by(name=p.category).first(); p.actual_weight=x.actual_weight;p.final_amount=round(x.actual_weight*cat.rate,2);p.status='Completed'
 batch=Batch(code='REC-'+datetime.utcnow().strftime('%Y')+'-'+secrets.token_hex(3).upper(),pickup_id=p.id,category=p.category,quantity=x.actual_weight,collector_id=u.id);db.add(batch)
 db.add(Notice(user_id=p.customer_id,message=f'Collection recorded: {x.actual_weight:g} {p.unit} at ₹{cat.rate:g}/{p.unit}. Estimated final value ₹{p.final_amount:g}.'))
 db.commit();return {'pickup':pickup_json(p,db,u),'rate':cat.rate,'batch_id':batch.code}
@app.get('/api/collector/summary')
def collector_summary(u:User=Depends(role('collector')),db:Session=Depends(get_db)):
 ps=db.query(Pickup).filter_by(collector_id=u.id).all();return {'new_requests':db.query(Pickup).filter_by(status='Finding Collector').count(),'active':sum(p.status not in ['Completed','Cancelled'] for p in ps),'completed':sum(p.status=='Completed' for p in ps),'earnings':round(sum(p.final_amount or 0 for p in ps if p.status=='Completed'),2)}
@app.get('/api/materials')
def materials(u:User=Depends(current_user),db:Session=Depends(get_db)):
 q=db.query(Batch)
 if u.role=='collector': q=q.filter_by(collector_id=u.id)
 if u.role=='recycler': q=q.filter((Batch.status=='Listed')|(Batch.recycler_id==u.id))
 return [{'id':b.id,'code':b.code,'pickup_code':db.get(Pickup,b.pickup_id).code,'category':b.category,'quantity':b.quantity,'status':b.status,'collector':db.get(User,b.collector_id).name,'recycler':db.get(User,b.recycler_id).name if b.recycler_id else None} for b in q.order_by(Batch.created_at.desc()).all()]
@app.post('/api/materials/{bid}/accept')
def accept_batch(bid:int,u:User=Depends(role('recycler')),db:Session=Depends(get_db)):
 if not u.verified: raise HTTPException(403,'Your recycler account needs verification.')
 b=db.get(Batch,bid)
 if not b or b.status!='Listed': raise HTTPException(409,'This material batch is no longer available.')
 b.recycler_id=u.id;b.status='Received';notify(db,b.collector_id,f'Recycler {u.name} accepted batch {b.code}.');db.commit();return {'ok':True,'status':b.status}
@app.put('/api/materials/{bid}/status')
def batch_status(bid:int,x:dict,u:User=Depends(role('recycler')),db:Session=Depends(get_db)):
 b=db.get(Batch,bid)
 if not b or b.recycler_id!=u.id: raise HTTPException(404,'Batch not assigned to your recycler account.')
 target=x.get('status')
 if target not in ['Processing','Recycled'] or (target=='Recycled' and b.status!='Processing'): raise HTTPException(400,'That batch status update is not available.')
 b.status=target;db.commit();return {'ok':True,'status':b.status}
@app.get('/api/notifications')
def notifications(u:User=Depends(current_user),db:Session=Depends(get_db)):
 return [{'id':n.id,'message':n.message,'read':n.read,'created_at':n.created_at.isoformat()} for n in db.query(Notice).filter_by(user_id=u.id).order_by(Notice.created_at.desc()).limit(100)]
@app.put('/api/notifications/{nid}/read')
def read_notice(nid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):
 n=db.query(Notice).filter_by(id=nid,user_id=u.id).first()
 if not n: raise HTTPException(404,'Notification not found.')
 n.read=True;db.commit();return {'ok':True}
@app.post('/api/uploads')
def upload(files:list[UploadFile]=File(...),u:User=Depends(current_user)):
 out=[]
 for f in files[:5]:
  if f.content_type not in ['image/jpeg','image/png','image/webp']: raise HTTPException(400,'Use JPG, PNG or WebP images.')
  data=f.file.read(5*1024*1024+1)
  if len(data)>5*1024*1024: raise HTTPException(400,'Each image must be smaller than 5 MB.')
  name=secrets.token_hex(12)+'.'+f.filename.rsplit('.',1)[-1].lower();(UPLOAD_DIR/name).write_bytes(data);out.append('/uploads/'+name)
 return {'images':out}
@app.post('/api/complaints')
def create_complaint(x:ComplaintIn,u:User=Depends(current_user),db:Session=Depends(get_db)):
 c=Complaint(user_id=u.id,category=x.category,description=x.description,pickup_code=x.pickup_code);db.add(c);db.commit();return {'id':c.id,'status':c.status}
@app.get('/api/admin/dashboard')
def admin_dashboard(u:User=Depends(role('admin')),db:Session=Depends(get_db)):
 return {'users':db.query(User).count(),'collectors':db.query(User).filter_by(role='collector',verified=True,status='active').count(),'recyclers':db.query(User).filter_by(role='recycler',verified=True).count(),'pending':db.query(User).filter(User.role.in_(['collector','recycler']),User.verified==False).count(),'pickups':db.query(Pickup).count(),'completed':db.query(Pickup).filter_by(status='Completed').count(),'waste_kg':round(sum(p.actual_weight or 0 for p in db.query(Pickup).filter_by(status='Completed').all()),2),'recycled_kg':round(sum(b.quantity for b in db.query(Batch).filter_by(status='Recycled').all()),2)}
@app.get('/api/admin/users')
def admin_users(u:User=Depends(role('admin')),db:Session=Depends(get_db)):
 return [user_json(a) for a in db.query(User).order_by(User.created_at.desc()).all()]
@app.put('/api/admin/users/{uid}/verification')
def verify_user(uid:int,x:dict,u:User=Depends(role('admin')),db:Session=Depends(get_db)):
 target=db.get(User,uid)
 if not target or target.role not in ['collector','recycler']: raise HTTPException(404,'Verification request not found.')
 target.verified=bool(x.get('verified'));notify(db,target.id,'Your account verification was approved.' if target.verified else 'Your account verification status was declined.');db.commit();return user_json(target)
@app.put('/api/admin/users/{uid}/status')
def user_status(uid:int,x:dict,u:User=Depends(role('admin')),db:Session=Depends(get_db)):
 target=db.get(User,uid)
 if not target: raise HTTPException(404,'User not found.')
 target.status=x.get('status','active');db.commit();return user_json(target)
@app.put('/api/admin/categories/{cid}/price')
def update_price(cid:int,x:RateIn,u:User=Depends(role('admin')),db:Session=Depends(get_db)):
 c=db.get(Category,cid)
 if not c or x.rate<0: raise HTTPException(400,'Enter a valid price.')
 c.rate=x.rate;db.commit();return {'id':c.id,'name':c.name,'rate':c.rate}
@app.get('/api/admin/complaints')
def complaints(u:User=Depends(role('admin')),db:Session=Depends(get_db)):
 return [{'id':c.id,'user':db.get(User,c.user_id).name,'category':c.category,'description':c.description,'pickup_code':c.pickup_code,'status':c.status} for c in db.query(Complaint).order_by(Complaint.created_at.desc()).all()]
@app.put('/api/admin/complaints/{cid}')
def update_complaint(cid:int,x:dict,u:User=Depends(role('admin')),db:Session=Depends(get_db)):
 c=db.get(Complaint,cid);target=x.get('status')
 if not c or target not in ['In Review','Resolved']: raise HTTPException(400,'Support request or status is invalid.')
 c.status=target;notify(db,c.user_id,f'Your support request is now {target.lower()}.');db.commit();return {'id':c.id,'status':c.status}
@app.get('/api/impact')
def impact(u:User=Depends(current_user),db:Session=Depends(get_db)):
 ps=db.query(Pickup).filter_by(status='Completed').all(); ours=[p for p in ps if p.customer_id==u.id or p.collector_id==u.id]
 return {'diverted_kg':round(sum(p.actual_weight or 0 for p in ours),2),'pickups':len(ours),'recycled_kg':round(sum(b.quantity for b in db.query(Batch).filter_by(status='Recycled').all()),2)}
