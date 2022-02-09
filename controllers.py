from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi import security
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED
from auth import auth

import db
from model import User,Task

import hashlib
import re

from mycalender import MyCalender

pattern = re.compile(r'\w{4,20}')  # 任意の4~20の英数字を示す正規表現
pattern_pw = re.compile(r'\w{6,20}')  # 任意の6~20の英数字を示す正規表現
pattern_mail = re.compile(r'^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$')  # e-mailの正規表現

app = FastAPI(
    title = "Todoアプリケーション",
    description="FastAPIチュートリアル",
    version="0"
)

templates = Jinja2Templates(directory="templates")
jinja_env = templates.env

security = HTTPBasic()

def index(request: Request):
    return templates.TemplateResponse("index.html",{"request":request})

def admin(request:Request, credentials: HTTPBasicCredentials = Depends(security)):

    username = auth(credentials)
    password = hashlib.md5(credentials.password.encode()).hexdigest()

    today = datetime.now()
    next_w = today + timedelta(days=7)
    
    user = db.session.query(User).filter(User.username == username).first()
    task = db.session.query(Task).filter(Task.user_id==user.id).all() if user is not None else []
    db.session.close()

    if user is None or user.password != password:
        error = "ユーザー名orパスワードが間違っています"
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Basic"},
        )
        
    cal = MyCalender(username,{t.deadline.strftime('%Y%m%d'):t.done for t in task})
    cal = cal.formatyear(today.year,4)
    task = [t for t in task if today <= t.deadline <= next_w]
    links = [t.deadline.strftime('/todo/'+username+'/%Y/%m/%d') for t in task]  # 直近の予定リンク

    return templates.TemplateResponse('admin.html',
                                      {'request': request,
                                       'user': user,
                                       'task': task,
                                       'links': links,
                                       'calender': cal})


async def register(request: Request):
    print(request.method)
    if request.method == "GET":
        return templates.TemplateResponse("register.html",{"request":request,
                                                            "username":"",
                                                            "error":[]})
    if request.method == "POST":
        data = await request.form()
        username = data.get('username')
        password = data.get('password')
        password_tmp = data.get('password_tmp')
        mail = data.get('mail')
        error = []
 
        tmp_user = db.session.query(User).filter(User.username == username).first()
 
        # 怒涛のエラー処理
        if tmp_user is not None:
            error.append('同じユーザ名のユーザが存在します。')
        if password != password_tmp:
            error.append('入力したパスワードが一致しません。')
        if pattern.match(username) is None:
            error.append('ユーザ名は4~20文字の半角英数字にしてください。')
        if pattern_pw.match(password) is None:
            error.append('パスワードは6~20文字の半角英数字にしてください。')
        if pattern_mail.match(mail) is None:
            error.append('正しくメールアドレスを入力してください。')
 
        # エラーがあれば登録ページへ戻す
        if error:
            return templates.TemplateResponse('register.html',
                                              {'request': request,
                                               'username': username,
                                               'error': error})
 
        # 問題がなければユーザ登録
        user = User(username, password, mail)
        db.session.add(user)
        db.session.commit()
        db.session.close()
 
        return templates.TemplateResponse('complete.html',
                                          {'request': request,
                                           'username': username})
        
def detail(request: Request, username, year, month, day,credentials:HTTPBasicCredentials=Depends(security)):

    user_auth = auth(credentials)
    if user_auth != username:
        return RedirectResponse("/")
    
    user = db.session.query(User).filter(User.username == username).first()
    task = db.session.query(Task).filter(Task.user_id == user.id).all()
    db.session.close()
    
    theday = '{}{}{}'.format(year, month.zfill(2), day.zfill(2))
    task = [t for t in task if t.deadline.strftime('%Y%m%d') == theday]

    return templates.TemplateResponse('detail.html',
                                      {'request': request,
                                       'username': username,
                                       'task': task,
                                       'year': year,
                                       'month': month,
                                       'day': day})

async def done(request: Request, credentials: HTTPBasicCredentials=Depends(security)):
    username = auth(credentials)
    user = db.session.query(User).filter(User.username == username).first()
    task = db.session.query(Task).filter(Task.user_id == user.id).all()
    
    data = await request.form()
    t_dones = data.getlist('done[]')
    
    for t in task:
        if str(t.id) in t_dones:
            t.done = True
    
    db.session.commit()
    db.session.close()
    
    return RedirectResponse('/admin',status_code=303)

async def add(request: Request, credentials: HTTPBasicCredentials=Depends(security)):
    username = auth(credentials)
    
    user = db.session.query(User).filter(User.username == username).first()
    
    data = await request.form()
    year = int(data['year'])
    month = int(data['month'])
    day = int(data['day'])
    hour = int(data['hour'])
    minute = int(data['minute'])

    deadline = datetime(year=year, month=month, day=day,
                        hour=hour, minute=minute)

    task = Task(user.id, data['content'], deadline)
    db.session.add(task)
    db.session.commit()
    db.session.close()

    return RedirectResponse('/admin',status_code=303)

def delete(request: Request, t_id, credentials: HTTPBasicCredentials = Depends(security)):
    username = auth(credentials)

    user = db.session.query(User).filter(User.username == username).first()
    task = db.session.query(Task).filter(Task.id == t_id).first()

    if task.user_id != user.id:
        return RedirectResponse(url='/admin',status_code=303)

    db.session.delete(task)
    db.session.commit()
    db.session.close()

    return RedirectResponse(url='/admin',status_code=303)
    
