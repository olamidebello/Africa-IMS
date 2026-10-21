#!/usr/bin/env python3
"""Operator-only account bootstrap and password recovery. Passwords never appear in arguments."""
import sys, pathlib, getpass
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from app import db,generate_password_hash
mode=sys.argv[1] if len(sys.argv)>1 else 'create'
email=input('Account email: ').strip().lower()
pw=getpass.getpass('New password (12+ characters): ')
if len(pw)<12:raise SystemExit('Password must be at least 12 characters')
with db() as c:
 if mode=='reset':
  if not c.execute('UPDATE users SET password=? WHERE email=?',(generate_password_hash(pw),email)).rowcount:raise SystemExit('Account not found')
  c.execute("INSERT INTO audit(action,entity) VALUES('operator_password_reset',?)",(email,))
 else:
  name=input('Administrator name: ').strip()
  c.execute("INSERT INTO users(tenant,name,email,password,role) VALUES(1,?,?,?,'super_admin')",(name,email,generate_password_hash(pw)))
print('Account updated successfully.')
