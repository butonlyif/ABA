import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("password")
args = parser.parse_args()
if len(args.password) < 12:
    raise SystemExit("专家密码至少需要 12 个字符")

db = SessionLocal()
user = db.scalar(select(User).where(User.username == args.username))
if user:
    user.role = "expert"
    user.password_hash = hash_password(args.password)
else:
    db.add(User(username=args.username, password_hash=hash_password(args.password), role="expert"))
db.commit()
db.close()
print(f"专家 {args.username} 已就绪")
