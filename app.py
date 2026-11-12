import os,json,sqlite3,secrets,hashlib,hmac,time,csv,io,math
from pathlib import Path
from datetime import datetime,timedelta
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse,JSONResponse,Response
from fastapi.staticfiles import StaticFiles
BASE=Path(__file__).parent
LOGIN_ATTEMPTS={}
DB=Path(os.getenv('DATA_DIR',str(BASE/'data')))/'platform.sqlite';DB.parent.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='江西物流一张网',version='1.0.0')
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def now():return datetime.now().isoformat(timespec='seconds')
def passwd(p,s):return hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),150000).hex()
with db() as c:
 c.executescript('CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,kind TEXT NOT NULL,data TEXT NOT NULL,owner TEXT NOT NULL,version INTEGER DEFAULT 1);CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY,salt TEXT,hash TEXT,role TEXT,company TEXT);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,name TEXT,expires REAL);CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,who TEXT,action TEXT,target TEXT,created TEXT);')
 for name,role,company in [('admin','admin','省级平台'),('enterprise','enterprise','江西铜业物流')]:
  if not c.execute('select 1 from users where name=?',(name,)).fetchone():
   salt=secrets.token_hex(16);p=os.getenv('DEMO_ADMIN_PASSWORD' if role=='admin' else 'DEMO_ENTERPRISE_PASSWORD','Demo@2026!');c.execute('insert into users values(?,?,?,?,?)',(name,salt,passwd(p,salt),role,company))
 if not c.execute('select 1 from records limit 1').fetchone():
  places=[('南昌向塘国际陆港',115.927,28.429),('九江港城西港区',115.926,29.713),('赣州国际陆港',114.788,25.839),('宜春冷链集配中心',114.401,27.804),('上饶铁路物流园',117.98,28.448),('吉安港物流枢纽',114.998,27.115)]
  for i in range(1,37):
   a=places[(i-1)%6];b=places[i%6];company=['江西铜业物流','省港口集团','江西供销冷链'][i%3];status=['待响应','对接中','已承接','已关闭'][i%4]
   x={'title':['铜精矿公铁联运','冷链生鲜运输','工业原料仓运协同','农产品干线配送'][i%4],'origin':a[0],'destination':b[0],'cargo':['铜精矿','冷链生鲜','工业原料','农产品'][i%4],'weight':80+i*12,'mode':['公铁联运','公水联运','公路运输'][i%3],'company':company,'status':status,'price':12000+i*380,'created':now(),'deadline':(datetime.now()+timedelta(days=12)).date().isoformat(),'description':'模拟业务数据，仅用于平台功能演示。','lat':a[2],'lng':a[1]}
   c.execute('insert into records values(?,?,?,?,1)',(f'DMD-2026-{i:04}','demands',json.dumps(x,ensure_ascii=False),company))
   y={**x,'title':'联运运输任务 '+str(i),'status':['在途','待发运','已签收','异常'][i%4],'progress':[62,0,100,38][i%4],'eta':(datetime.now()+timedelta(hours=i+8)).isoformat(timespec='minutes'),'sourceId':f'YL-2026-{1000+i}'}
   c.execute('insert into records values(?,?,?,?,1)',(f'JX-2026-{i:04}','waybills',json.dumps(y,ensure_ascii=False),company))
  for i in range(1,19):
   a=places[(i-1)%6];x={'title':a[0]+[' · 标准仓',' · 冷链仓',' · 综合运力'][i%3],'origin':a[0],'company':['江西铜业物流','省港口集团','江西供销冷链'][i%3],'mode':['普通仓','冷库','车船运力'][i%3],'capacity':6000+i*500,'available':1800+i*80,'temperature':'-18℃～0℃' if i%3==1 else '常温','status':'已认证','lat':a[2],'lng':a[1],'price':18+i,'description':'已接入模拟资源，实时可用能力需资源方确认。','created':now()}
   c.execute('insert into records values(?,?,?,?,1)',(f'RES-{i:04}','resources',json.dumps(x,ensure_ascii=False),x['company']))
  for i,title in enumerate(['江西省物流降本增效政策服务指南','多式联运示范业务申报指引','冷链仓储设施建设服务指南','城乡配送资源共用服务说明','铁路货运运价查询指南','物流企业绿色运输服务指南'],1):
   x={'title':title,'department':['省发展改革委','省交通运输厅','省商务厅'][i%3],'status':'示例政策','mode':['多式联运','冷链仓储','公共服务'][i%3],'created':now(),'description':'这是演示政策内容，不是正式政策文件。真实资格、补助金额及有效期须查阅主管部门权威发布。平台提供政策检索、条件自测和申报入口协同。','deadline':'待权威核验'}
   c.execute('insert into records values(?,?,?,?,1)',(f'POL-{i:04}','policies',json.dumps(x,ensure_ascii=False),'public'))
  for i in range(1,9):
   x={'title':['运输节点超时','冷链温度异常','数据接口延迟','港区交接待确认'][i%4],'status':['待确认','处理中','待复核','已关闭'][i%4],'level':['高','中','低'][i%3],'waybill':f'JX-2026-{i:04}','company':'江西铜业物流','created':now(),'description':'模拟预警；请核实来源节点与业务情况后反馈。'}
   c.execute('insert into records values(?,?,?,?,1)',(f'ALT-{i:04}','alerts',json.dumps(x,ensure_ascii=False),'江西铜业物流'))
  for i,title in enumerate(['交通路网数据服务','港口节点事件交换','企业TMS运单同步','冷链仓储资源交换','铁路班列计划服务'],1):
   x={'title':title,'status':['正常','正常','延迟'][i%3],'company':'平台接入中心','mode':'REST API','success':99.2+i/10,'latency':80+i*18,'created':now(),'description':'模拟接入服务，没有实际连接政府或企业生产系统。'}
   c.execute('insert into records values(?,?,?,?,1)',(f'API-{i:04}','interfaces',json.dumps(x,ensure_ascii=False),'platform'))
  for i in range(1,5):
   x={'title':['企业认证材料核验','运输异常协同处置','资源共享授权申请','政策咨询服务'][i-1],'company':'江西铜业物流','status':['待受理','处理中','待复核','已关闭'][i-1],'created':now(),'description':'模拟服务工单。'}
   c.execute('insert into records values(?,?,?,?,1)',(f'TKT-{i:04}','tickets',json.dumps(x,ensure_ascii=False),'江西铜业物流'))
def user(req):
 token=req.cookies.get('jx_session','')
 with db() as c:r=c.execute('select u.* from sessions s join users u on u.name=s.name where s.token=? and s.expires>?',(token,time.time())).fetchone()
 if not r:raise HTTPException(401,'请先登录')
 return dict(r)
def audit(c,u,action,target):c.execute('insert into audit(who,action,target,created) values(?,?,?,?)',(u['name'],action,target,now()))
def visible(u,r):return u['role']=='admin' or r['owner'] in (u['company'],'public') or r['kind']=='resources'
def record(r):return {'id':r['id'],'kind':r['kind'],'version':r['version'],**json.loads(r['data'])}
KINDS={'demands','resources','waybills','policies','alerts','interfaces','tickets'}
@app.get('/health')
def health():return {'status':'ok','database':'sqlite','mode':'simulation'}
@app.post('/api/login')
async def login(req:Request):
 ip=req.client.host if req.client else 'unknown';attempts=LOGIN_ATTEMPTS.setdefault(ip,[]);attempts[:]=[t for t in attempts if time.time()-t<60]
 if len(attempts)>=10:raise HTTPException(429,'登录尝试过于频繁，请一分钟后重试')
 attempts.append(time.time())
 x=await req.json();name=str(x.get('username',''));p=str(x.get('password',''))
 with db() as c:
  r=c.execute('select * from users where name=?',(name,)).fetchone()
  if not r or not hmac.compare_digest(r['hash'],passwd(p,r['salt'])):raise HTTPException(401,'账号或密码不正确')
  token=secrets.token_urlsafe(40);c.execute('insert into sessions values(?,?,?)',(token,name,time.time()+28800));audit(c,dict(r),'登录','account')
 response=JSONResponse({'name':r['name'],'role':r['role'],'company':r['company']});response.set_cookie('jx_session',token,httponly=True,samesite='strict',secure=req.url.scheme=='https',max_age=28800);return response
@app.post('/api/logout')
def logout(req:Request):
 with db() as c:c.execute('delete from sessions where token=?',(req.cookies.get('jx_session',''),))
 r=JSONResponse({'ok':True});r.delete_cookie('jx_session');return r
@app.get('/api/me')
def me(req:Request):
 u=user(req);return {k:u[k] for k in ['name','role','company']}
@app.get('/api/config')
def config(req:Request):
 user(req);return {'amapKey':os.getenv('AMAP_WEB_KEY',''),'amapSecurityCode':os.getenv('AMAP_SECURITY_CODE',''),'simulation':True,'persistentStorage':bool(os.getenv('DATA_DIR'))}
@app.get('/api/modules')
def modules(req:Request):
 user(req);return json.loads((BASE/'modules.json').read_text())
@app.get('/api/data/{kind}')
def listing(kind:str,req:Request,q:str='',status:str='',page:int=1,size:int=100):
 u=user(req)
 if kind not in KINDS:raise HTTPException(404)
 if kind=='interfaces' and u['role']!='admin':raise HTTPException(403,'仅平台管理员可访问接口管理')
 with db() as c:rows=[record(r) for r in c.execute('select * from records where kind=? order by id desc',(kind,)) if visible(u,r)]
 if q:rows=[r for r in rows if q.lower() in json.dumps(r,ensure_ascii=False).lower()]
 if status:rows=[r for r in rows if r.get('status')==status]
 size=min(200,max(1,size));page=max(1,page);return {'items':rows[(page-1)*size:page*size],'total':len(rows),'page':page}
@app.get('/api/data/{kind}/{rid}')
def detail(kind:str,rid:str,req:Request):
 u=user(req)
 with db() as c:r=c.execute('select * from records where kind=? and id=?',(kind,rid)).fetchone()
 if not r or not visible(u,r):raise HTTPException(404,'记录不存在或无权访问')
 x=record(r)
 if kind=='waybills':x['events']=[{'name':n,'time':(datetime.now()-timedelta(hours=25-i*6)).isoformat(timespec='minutes'),'status':'已完成' if i<int(x['progress']/25) else '计划节点','source':'模拟事件'} for i,n in enumerate(['货主出库','短驳到站','干线运输','目的站交接','签收交付'])]
 return x
@app.post('/api/data/{kind}')
async def create(kind:str,req:Request):
 u=user(req)
 if kind not in KINDS:raise HTTPException(404)
 if u['role']!='admin' and kind not in {'demands','resources','tickets'}:raise HTTPException(403)
 x=await req.json()
 if not isinstance(x.get('title'),str) or not x['title'].strip() or len(x['title'])>200:raise HTTPException(422,'标题必填，最多200字')
 if kind=='demands':
  if not x.get('origin') or not x.get('destination') or x['origin']==x['destination']:raise HTTPException(422,'请选择不同的起讫点')
  try:w=float(x.get('weight',0))
  except (TypeError,ValueError):raise HTTPException(422,'货物重量格式错误')
  if not math.isfinite(w) or w<=0:raise HTTPException(422,'货物重量必须为正数')
 if kind=='resources':
  try:cap=float(x.get('capacity',0));avail=float(x.get('available',0))
  except (TypeError,ValueError):raise HTTPException(422,'容量格式错误')
  if not math.isfinite(cap) or not math.isfinite(avail) or cap<=0 or avail<0 or avail>cap:raise HTTPException(422,'总容量必须为正数，可用量应介于零和总容量之间')
  x['capacity']=cap;x['available']=avail
 x['company']=u['company'];x['created']=now();x['status']='待响应' if kind=='demands' else '待审核' if kind=='resources' else '待受理';rid=kind[:3].upper()+'-'+secrets.token_hex(5).upper()
 with db() as c:c.execute('insert into records values(?,?,?,?,1)',(rid,kind,json.dumps(x,ensure_ascii=False),u['company']));audit(c,u,'创建',rid)
 return {'id':rid,'version':1,**x}
TRANS={'demands':{'待响应':['对接中','已关闭'],'对接中':['已承接','已关闭'],'已承接':['已关闭']},'alerts':{'待确认':['处理中'],'处理中':['待复核'],'待复核':['已关闭','处理中'],'已关闭':['待确认']},'tickets':{'待受理':['处理中'],'处理中':['待复核'],'待复核':['已关闭','处理中']},'resources':{'待审核':['已认证','已驳回'],'已认证':['已停用'],'已停用':['待审核']}}
@app.patch('/api/data/{kind}/{rid}')
async def change(kind:str,rid:str,req:Request):
 u=user(req);x=await req.json()
 with db() as c:
  r=c.execute('select * from records where kind=? and id=?',(kind,rid)).fetchone()
  if not r or not visible(u,r):raise HTTPException(404)
  if u['role']!='admin' and (r['owner']!=u['company'] or kind not in {'demands','tickets'}):raise HTTPException(403)
  if x.get('version')!=r['version']:raise HTTPException(409,'记录已变更，请刷新后重试')
  data=json.loads(r['data']);status=x.get('status');allowed=TRANS.get(kind,{}).get(data['status'],[])
  if status not in allowed:raise HTTPException(422,'当前状态不允许此操作')
  if not str(x.get('reason','')).strip():raise HTTPException(422,'请填写处理意见')
  data.update(status=status,lastReason=str(x['reason'])[:1000],updated=now());c.execute('update records set data=?,version=version+1 where id=?',(json.dumps(data,ensure_ascii=False),rid));audit(c,u,'状态变更：'+status,rid)
 return {'ok':True,'status':status,'version':r['version']+1}
@app.post('/api/quotes')
async def quote(req:Request):
 u=user(req);x=await req.json();rid=x.get('demandId','')
 with db() as c:
  r=c.execute('select * from records where id=? and kind="demands"',(rid,)).fetchone()
  if not r or not visible(u,r):raise HTTPException(404)
  data=json.loads(r['data'])
  try:price=float(x.get('price',0))
  except (ValueError,TypeError):raise HTTPException(422,'报价格式错误')
  if not math.isfinite(price) or price<=0:raise HTTPException(422,'报价须为正数')
  if data['status'] not in ['待响应','对接中']:raise HTTPException(422,'需求已关闭或已承接')
  data.setdefault('quotes',[]).append({'id':secrets.token_hex(5),'price':price,'company':u['company'],'created':now(),'note':str(x.get('note',''))[:500]});data['status']='对接中';c.execute('update records set data=?,version=version+1 where id=?',(json.dumps(data,ensure_ascii=False),rid));audit(c,u,'提交参考报价',rid)
 return {'ok':True}
@app.post('/api/plans')
async def plans(req:Request):
 user(req);x=await req.json()
 if not x.get('origin') or not x.get('destination') or x['origin']==x['destination']:raise HTTPException(422,'请选择不同的起讫枢纽')
 try:w=float(x.get('weight',100))
 except (ValueError,TypeError):raise HTTPException(422,'重量格式错误')
 if not math.isfinite(w) or w<=0:raise HTTPException(422,'重量必须大于零')
 return {'simulation':True,'plans':[{'id':'PLAN-'+str(i),'name':n,'mode':m,'cost':round(w*c),'hours':h,'carbon':round(w*k,1),'segments':[x['origin'],'向塘国际陆港' if i==0 else '九江港换装节点' if i==1 else '高速公路干线',x['destination']],'notice':'模拟网络估算，非实时运价或可订舱位；不构成运输承诺。'} for i,(n,m,c,h,k) in enumerate([('均衡推荐','公铁联运',128,26,3.2),('成本优选','公水联运',98,42,2.5),('时效优先','公路直达',176,12,6.8)])]}
@app.get('/api/export/{kind}')
def export(kind:str,req:Request):
 data=listing(kind,req,size=200)['items'];out=io.StringIO();wr=csv.writer(out);wr.writerow(['编号','名称','企业','状态','模拟数据'])
 for x in data:
  vals=[x['id'],x['title'],x.get('company',''),x.get('status',''),'是'];wr.writerow(["'"+str(v) if str(v).lstrip().startswith(('=','+','-','@')) else v for v in vals])
 return Response('\ufeff'+out.getvalue(),media_type='text/csv;charset=utf-8',headers={'Content-Disposition':f'attachment; filename="jiangxi-{kind}.csv"'})
@app.get('/api/audit')
def audits(req:Request):
 u=user(req)
 if u['role']!='admin':raise HTTPException(403)
 with db() as c:return {'items':[dict(x) for x in c.execute('select * from audit order by id desc limit 100')]}
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
@app.get('/')
def home():return FileResponse(BASE/'static/index.html')
