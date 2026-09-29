"""Seed clearly labeled local demo accounts. Set DEMO_PASSWORD before running."""
import os
from main import SessionLocal, User, Pickup, Category, pw_hash

password=os.getenv('DEMO_PASSWORD')
if not password or len(password)<12:
    raise SystemExit('Set DEMO_PASSWORD to a password with at least 12 characters.')
accounts=[
 ('Demo Customer','customer.demo@example.com','customer','Pune',True),
 ('Demo Kabadiwala','collector.demo@example.com','collector','Pune',True),
 ('Demo Recycler','recycler.demo@example.com','recycler','Pune',True),
 ('Demo Admin','admin.demo@example.com','admin','',True),
]
with SessionLocal() as db:
    records={}
    for name,email,role,city,verified in accounts:
        user=db.query(User).filter_by(email=email).first()
        if not user:
            user=User(name=name,email=email,role=role,city=city,phone='',verified=verified,password_hash=pw_hash(password))
            db.add(user); db.flush()
        records[role]=user
    if not db.query(Pickup).filter_by(code='DEMO-KBC-0001').first():
        cat=db.query(Category).filter_by(name='Paper').first()
        if not cat: raise SystemExit('Start the API once to initialize categories, then rerun this script.')
        db.add(Pickup(code='DEMO-KBC-0001',customer_id=records['customer'].id,category='Paper',subcategory='Cardboard',quantity=4,unit='kg',condition='Clean',address='Demo address, Pune (sample only)',city='Pune',date='2026-10-02',time='Morning · 9 am–12 pm',status='Finding Collector',notes='Seeded development example'))
    db.commit()
print('Demo accounts ready (all use DEMO_PASSWORD):')
for _,email,role,_,_ in accounts: print(f'  {role}: {email}')
