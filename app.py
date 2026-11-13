import os,json,sqlite3,secrets,hashlib,hmac,time,csv,io,math,re
from pathlib import Path
from datetime import datetime,timedelta
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse,JSONResponse,Response
from fastapi.staticfiles import StaticFiles
BASE=Path(__file__).parent
LOGIN_ATTEMPTS={}
DB=Path(os.getenv('DATA_DIR',str(BASE/'data')))/'platform.sqlite';DB.parent.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='江西物流一张网',version='2.0.0')
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
 # Add a small cross-region sample set on existing databases as well as clean installs.
 # These records are clearly simulated and let the demo show that the network is not
 # limited to Jiangxi endpoints.
 national=[
  ('DMD-GLOBAL-0001','JX-INT-0001','省际 / 全国','南昌至武汉铁路干线运输','南昌站','武汉站','铁路运输','铜材',186,'省际铁路轨道规划示例；铁路货运受理、班列时刻、舱位及运价需由承运方确认。','','铁路'),
  ('DMD-GLOBAL-0002','JX-INT-0002','省际 / 全国','南昌冷链公路至广州白云','南昌向塘国际陆港','广州白云区','公路运输','冷链食品',42,'温控与货车通行安排需承运方确认。','','公路'),
  ('DMD-GLOBAL-0003','JX-INT-0003','国际 / 跨境','江西铜材出口至新加坡','九江港城西港区','Singapore Port','国际多式联运','铜材',520,'国际水运与口岸节点仅作路线计划示例；海外地名需核验，未接入港航实时数据。','洋山深水港,上海市,中国','公路,水路')]
 national += [
  ('DMD-GLOBAL-0004','JX-INT-0004','省际 / 全国','南昌至上海铁路联运','南昌站','上海虹桥站','铁路运输','电子产品',96,'跨省铁路轨道线路示例；班次、货运承接和运价需由铁路承运方确认。','','铁路'),
  ('DMD-GLOBAL-0005','JX-INT-0005','省际 / 全国','上海至南昌返程铁路运单','上海虹桥站','南昌站','铁路运输','日用消费品',128,'跨省返程运单示例；班次、货运承接和运价需由铁路承运方确认。','','铁路'),
  ('DMD-GLOBAL-0006','JX-INT-0006','省际 / 全国','九江至杭州冷链公路运单','九江港城西港区','杭州市','公路运输','冷链食品',26,'跨省公路运输需求示例，温控、车型及通行安排需承运方确认。','','公路'),
  ('DMD-GLOBAL-0007','JX-INT-0007','省际 / 全国','赣州至深圳工业原料运输','赣州国际陆港','深圳市','公路运输','工业原料',74,'跨省公路运输需求示例，车型、时效和运价需承运方确认。','','公路'),
  ('DMD-GLOBAL-0008','JX-INT-0008','省际 / 全国','南京至南昌回程运单','南京市','南昌向塘国际陆港','公路运输','包装材料',38,'省外货源回程运输示例，装卸条件和交付时限需承运方确认。','','公路')]
 for did,wid,scope,title,origin,destination,mode,cargo,weight,description,nodes,modes in national:
  if not c.execute('select 1 from records where id=?',(did,)).fetchone():
   base={'scope':scope,'title':title,'origin':origin,'destination':destination,'cargo':cargo,'weight':weight,'mode':mode,'routeNodes':nodes,'routeModes':modes,'company':'江西铜业物流','status':'待响应','price':0,'created':now(),'deadline':(datetime.now()+timedelta(days=18)).date().isoformat(),'description':description}
   if did in ('DMD-GLOBAL-0001','DMD-GLOBAL-0004','DMD-GLOBAL-0005'):
    coords={'南昌站':[115.912,28.665],'武汉站':[114.424,30.625],'上海虹桥站':[121.327,31.2]}
    base['originCoords']=coords[origin];base['destinationCoords']=coords[destination];base['routeNodes']='';base['routeModes']='铁路'
   c.execute('insert into records values(?,?,?,?,1)',(did,'demands',json.dumps(base,ensure_ascii=False),'江西铜业物流'))
   way={**base,'title':title+' · 运输任务','status':'在途','progress':43,'eta':(datetime.now()+timedelta(hours=30)).isoformat(timespec='minutes'),'sourceId':'EXT-'+wid}
   c.execute('insert into records values(?,?,?,?,1)',(wid,'waybills',json.dumps(way,ensure_ascii=False),'江西铜业物流'))
 # Refresh the original nationwide rail sample on already-initialized databases too.
 rail_coords={'南昌站':[115.912,28.665],'武汉站':[114.424,30.625]}
 for rid in ('DMD-GLOBAL-0001','JX-INT-0001'):
  row=c.execute('select data from records where id=?',(rid,)).fetchone()
  if row:
   sample=json.loads(row['data']);sample.update({'scope':'省际 / 全国','title':'南昌至武汉铁路干线运输'+(' · 运输任务' if rid=='JX-INT-0001' else ''),'origin':'南昌站','destination':'武汉站','mode':'铁路运输','routeNodes':'','routeModes':'铁路','originCoords':rail_coords['南昌站'],'destinationCoords':rail_coords['武汉站'],'description':'省际铁路轨道规划示例；铁路货运受理、班列时刻、舱位及运价需由承运方确认。'})
   c.execute('update records set data=? where id=?',(json.dumps(sample,ensure_ascii=False),rid))
 for did,wid in [('DMD-GLOBAL-0004','JX-INT-0004'),('DMD-GLOBAL-0005','JX-INT-0005')]:
  for rid in (did,wid):
   row=c.execute('select data from records where id=?',(rid,)).fetchone()
   if row:
    sample=json.loads(row['data']);sample.update({'originCoords':{'南昌站':[115.912,28.665],'上海虹桥站':[121.327,31.2]}[sample['origin']],'destinationCoords':{'南昌站':[115.912,28.665],'上海虹桥站':[121.327,31.2]}[sample['destination']],'routeNodes':'','routeModes':'铁路'})
    c.execute('update records set data=? where id=?',(json.dumps(sample,ensure_ascii=False),rid))
 for rid in ('DMD-GLOBAL-0003','JX-INT-0003'):
  row=c.execute('select data from records where id=?',(rid,)).fetchone()
  if row:
   sample=json.loads(row['data']);sample['routeNodes']='洋山深水港[121.99,30.62]';sample['destinationCoords']=[103.82,1.26];sample['routeModes']='公路,水路'
   c.execute('update records set data=? where id=?',(json.dumps(sample,ensure_ascii=False),rid))
 # Explicit example itinerary; these stations are declared sample business nodes, never inferred transfers.
 for rid,kind in [('DMD-MULTI-0001','demands'),('JX-MULTI-0001','waybills')]:
  if not c.execute('select 1 from records where id=?',(rid,)).fetchone():
   d={'title':'南昌至上海公铁联运（分段线路示例）','origin':'南昌向塘国际陆港','destination':'上海洋山深水港','destinationCoords':[121.99,30.62],'routeNodes':'南昌站[115.912,28.665];上海虹桥站[121.327,31.2]','routeModes':'公路,铁路,公路','mode':'公铁联运','scope':'跨省 / 全国','cargo':'电子产品','weight':20,'company':'江西铜业物流','status':'在途' if kind=='waybills' else '待响应','progress':40,'created':now(),'description':'模拟运单，节点为明确指定的线路查询样例；铁路为轨道规划参考，不代表货运受理或班列任务。'}
   c.execute('insert into records values(?,?,?,?,1)',(rid,kind,json.dumps(d,ensure_ascii=False),'江西铜业物流'))
 for rid in ('DMD-MULTI-0001','JX-MULTI-0001'):
  row=c.execute('select data from records where id=?',(rid,)).fetchone()
  if row:
   d=json.loads(row['data']);d.update(destination='上海洋山深水港',destinationCoords=[121.99,30.62]);c.execute('update records set data=? where id=?',(json.dumps(d,ensure_ascii=False),rid))
 # Normalize demo supply fields so matching never confuses warehouse area with transport tonnage.
 for row in c.execute('select id,data from records where kind="resources"').fetchall():
  d=json.loads(row['data']);kind=d.get('mode','');is_transport=kind in ('车船运力','普通货车','冷藏车','冷藏车运力','铁路运力','船舶运力') or d.get('resourceCategory')=='transport'
  d.setdefault('resourceCategory','transport' if is_transport else 'warehouse')
  d.setdefault('capacityUnit','吨' if is_transport else '㎡')
  d.setdefault('transportModes',['公路'] if kind in ('车船运力','普通货车','冷藏车','冷藏车运力') else ['铁路'] if kind=='铁路运力' else ['水运'] if kind=='船舶运力' else [])
  d.setdefault('coldChain','冷' in kind or '冷' in str(d.get('temperature','')))
  d.setdefault('temperatureRange',d.get('temperature') if d.get('coldChain') else None)
  d.setdefault('coverage',['江西省','全国']);d.setdefault('dataSource','演示资源样例')
  if d != json.loads(row['data']):c.execute('update records set data=? where id=?',(json.dumps(d,ensure_ascii=False),row['id']))
 demo_supplies=[
  ('RES-COLD-TRUCK-01',{'title':'赣州产地冷藏车队（模拟）','origin':'赣州市','company':'江西冷链运力示例','mode':'冷藏车运力','resourceCategory':'transport','transportModes':['公路'],'vehicleType':'冷藏车','capacity':120,'available':42,'capacityUnit':'吨','coldChain':True,'temperatureRange':'-18～+8℃（演示能力，实际须供方核验）','coverage':['江西省','全国'],'status':'已认证','price':3.6,'dataSource':'模拟匹配样例','description':'用于演示生鲜公路段温控运力匹配，不代表真实车辆或实时可约运力。'}),
  ('RES-FURNITURE-DOCK-01',{'title':'南康大件装卸与暂存点（模拟）','origin':'赣州市南康区','company':'南康家具物流示例','mode':'普通仓','resourceCategory':'warehouse','transportModes':[],'capacity':6000,'available':1600,'capacityUnit':'㎡','coldChain':False,'temperature':'常温','coverage':['江西省'],'status':'已认证','price':22,'dataSource':'模拟匹配样例','handlingEquipment':['叉车','装卸平台（需核验）'],'oversizeHandling':'大件长度、承重和装卸条件逐单确认','description':'用于展示家具临时仓储与装卸条件核验；面积和设备信息为演示数据。'}),
  ('RES-BULK-RAIL-01',{'title':'省际铁路大宗货运能力（待核验）','origin':'南昌铁路物流中心','company':'铁路运力接入示例','mode':'铁路运力','resourceCategory':'transport','transportModes':['铁路'],'capacity':1600,'available':780,'capacityUnit':'吨','coldChain':False,'coverage':['江西省','全国'],'status':'待核验','price':None,'dataSource':'模拟待核验资源','description':'铁路运量、车皮、班次和运价须向铁路承运方核实；当前记录不构成可订运力。'})]
 for rid,d in demo_supplies:
  if not c.execute('select 1 from records where id=?',(rid,)).fetchone():c.execute('insert into records values(?,?,?,?,1)',(rid,'resources',json.dumps({**d,'created':now()},ensure_ascii=False),d['company']))

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
def health():return {'status':'ok','database':'sqlite','mode':'simulation','version':'2.0.0','routeDetails':True,'realRoadRouting':True,'realRailTrackRouting':True,'seaRoutingConfigured':False,'seaRoutingMode':'port_sketch_only'}
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
 user(req);return {'amapKey':os.getenv('AMAP_WEB_KEY',''),'amapSecurityCode':os.getenv('AMAP_SECURITY_CODE',''),'amapRoadConfigured':bool(os.getenv('AMAP_WEB_SERVICE_KEY')),'railRoutingConfigured':True,'waterRoutingConfigured':False,'simulation':True,'persistentStorage':bool(os.getenv('DATA_DIR'))}
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
 if not x.get('origin') or not x.get('destination') or str(x['origin']).strip()==str(x['destination']).strip():raise HTTPException(422,'请选择不同的起讫地点')
 try:w=float(x.get('weight',100))
 except (ValueError,TypeError):raise HTTPException(422,'重量格式错误')
 if not math.isfinite(w) or w<=0:raise HTTPException(422,'重量必须大于零')
 if x.get('budget') not in (None,''):
  try:budget=float(x['budget'])
  except (ValueError,TypeError):raise HTTPException(422,'预算格式错误')
  if not math.isfinite(budget) or budget<0:raise HTTPException(422,'预算不能为负数')
 from route_service import build_route,parse_user_point
 from real_routes import apply_real_routes
 legs=x.get('legs') or []
 if not isinstance(legs,list) or len(legs)>8:raise HTTPException(422,'最多可配置8个连续运输段')
 if legs:
  if not legs:raise HTTPException(422,'请添加运输段')
  for i,leg in enumerate(legs):
   if not isinstance(leg,dict) or leg.get('mode') not in ('公路','铁路','水运'):raise HTTPException(422,'运输方式请选择公路、铁路或水运')
   if not str(leg.get('from','')).strip() or not str(leg.get('to','')).strip():raise HTTPException(422,'每段起讫节点不能为空')
   if str(leg['from']).strip()==str(leg['to']).strip():raise HTTPException(422,'同一运输段的起讫节点不能相同')
   if i and str(legs[i-1]['to']).strip()!=str(leg['from']).strip():raise HTTPException(422,'运输段必须连续，上一段终点须与下一段起点一致')
  clean_location=lambda v:re.sub(r'\s*\[[^]]+\]','',str(v)).strip()
  if clean_location(legs[0]['from'])!=clean_location(x['origin']) or clean_location(legs[-1]['to'])!=clean_location(x['destination']):raise HTTPException(422,'首段起点和末段终点须与上方起讫地点一致')
  mode_sets=[legs]
 else:
  requested=x.get('modes') or ['公路']
  if not isinstance(requested,list) or not requested or any(m not in ('公路','铁路','水运') for m in requested):raise HTTPException(422,'请至少选择公路、铁路或水运，可同时比较多种方式')
  if len(set(requested))!=len(requested):raise HTTPException(422,'运输方式不能重复')
  mode_sets=[[{'from':str(x['origin']).strip(),'to':str(x['destination']).strip(),'mode':m}] for m in requested]
 def endpoint(value):
  value=str(value).strip();coord=parse_user_point(value);name=re.sub(r'\s*\[[^]]+\]','',value).strip();return name,coord
 if x.get('plannedDeparture') and x.get('requiredArrival') and x['plannedDeparture']>x['requiredArrival']:raise HTTPException(422,'要求到达日期不能早于计划发运日期')
 routes=[]
 for ix,route_legs in enumerate(mode_sets):
  origin,oc=endpoint(route_legs[0]['from']);destination,dc=endpoint(route_legs[-1]['to'])
  multi=len(route_legs)>1;first_mode=route_legs[0]['mode']
  order={'id':f'QUERY-PLAN-{ix+1}','origin':origin,'destination':destination,'weight':w,'cargo':str(x.get('cargo',''))[:200],'mode':'多式联运' if multi else first_mode+'运输','routeModes':','.join(l['mode'] for l in route_legs),'routeNodes':';'.join(l['to'] for l in route_legs[:-1]),'title':'联运链路查询','created':now()}
  order.update({k:x.get(k) for k in ('loadType','plannedDeparture','requiredArrival','budget','requirements') if x.get(k) not in (None,'')})
  if oc:order['originCoords']=oc
  if dc:order['destinationCoords']=dc
  route=apply_real_routes(build_route(order,'demands'))
  route['name']=('指定联运链路' if multi else first_mode+'路线查询') if legs else first_mode+'路线查询'
  routes.append(route)
 if x.get('compareRoad') and legs and (len(legs)>1 or legs[0]['mode']!='公路'):
  order={**routes[0]['order'],'id':'QUERY-ROAD','routeNodes':'','routeModes':'公路','mode':'公路运输'}
  base=apply_real_routes(build_route(order,'demands'));base['name']='全程公路参照';routes.append(base)
 return {'plans':routes,'orderTemplate':{k:v for k,v in routes[0]['order'].items() if k not in ('id','created')},'notice':'路线按已选运输方式和实际起讫地点分别查询；已配置的联运按填写的分段顺序查询，不自动推断换装节点。承运班次、运价、舱位、货运受理和通行条件须由承运方确认。'}

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
def home():return FileResponse(BASE/'static/index.html',headers={'Cache-Control':'no-store, max-age=0'})

from route_service import register_routes
register_routes(app,db,user,visible,record)

@app.get('/api/matching/{rid}')
def matching(rid:str,req:Request):
 u=user(req)
 with db() as c:
  row=c.execute('select * from records where kind="demands" and id=?',(rid,)).fetchone()
  if not row or not visible(u,row):raise HTTPException(404,'需求不存在或无权访问')
  demand=record(row);resources=[record(r) for r in c.execute('select * from records where kind="resources"') if visible(u,r)]
 weight=float(demand.get('weight',0) or 0);requested=demand.get('routeModes') or ''
 modes=[x.strip() for x in re.split(r'[;,，；]+',str(requested)) if x.strip()]
 if not modes:
  m=str(demand.get('mode',''))
  modes=([v for v,key in [('公路','公'),('铁路','铁'),('水运','水') ] if key in m] if '联运' in m or '多式' in m else [m])
 aliases={'水路':'水运','海运':'水运','水路运输':'水运','铁路运输':'铁路','公路运输':'公路','航空运输':'航空'}
 modes=[aliases.get(x,x) for x in modes];modes=list(dict.fromkeys(modes))
 temp=str(demand.get('temperatureRequirement','') or '')
 requires_cold=not any(x in temp for x in ('无温控','无需温控','不需要冷链','常温')) and any(x in temp for x in ('冷藏','冷冻','冷链运输','温控运输'))
 requires_cold=requires_cold or ('冷链' in str(demand.get('cargo','')) and not any(x in temp for x in ('无温控','无需温控','常温')))
 hazardous=bool(demand.get('hazardous')) or bool(demand.get('hazardClass'))
 storage_needed=bool(demand.get('storageHours') or demand.get('storageAreaM2') or demand.get('storageVolumeM3') or demand.get('warehousingRequired'))
 result=[]
 for r in resources:
  is_transport=r.get('resourceCategory')=='transport' or r.get('mode') in ('车船运力','普通货车','冷藏车','冷藏车运力','铁路运力','船舶运力')
  category='transport' if is_transport else 'warehouse';available=float(r.get('available',0) or 0);capacity=float(r.get('capacity',0) or 0)
  supports=[aliases.get(str(x),str(x)) for x in (r.get('transportModes') or (['公路'] if r.get('mode') in ('车船运力','普通货车','冷藏车','冷藏车运力') else []))]
  compatible=[m for m in modes if m in supports];reasons=[];hard=[]
  if category=='transport':
   if not compatible:hard.append('供给运输方式不覆盖当前需求运输段')
   if available<=0:hard.append('当前可用运力为零或未提供')
   if requires_cold and not r.get('coldChain'):hard.append('需求要求温控，供给未声明冷链能力')
   if hazardous and not r.get('hazardousGoods'):hard.append('需求包含危险属性，供给未提交相应资质')
   if available<weight:reasons.append(f'可用{available:g}吨，少于需求{weight:g}吨；可协商分批/多车供给')
   if not compatible and supports:reasons.append('可提供方式：'+ '、'.join(supports))
   if compatible:reasons.append('可匹配运输段：'+ '、'.join(compatible))
   if requires_cold and r.get('coldChain'):
    actual=str(r.get('temperatureRange') or '')
    requested_range=str(demand.get('temperatureRange') or '')
    if requested_range and actual and actual!=requested_range:hard.append('温区未能核实一致：请由供方确认')
    elif not actual:hard.append('冷链能力已声明，但具体温区待供方核验')
    else:reasons.append('冷链能力及温区需随订单再次核验：'+actual)
   complete=bool(modes) and all(m in supports for m in modes)
   if modes and compatible and not complete:reasons.append('仅为部分运输段供给，不代表可独立完成整票多式联运')
   capacity_ok=available>=weight
   eligible=not hard and capacity_ok and bool(compatible) and r.get('status')=='已认证' and demand.get('status') not in ('已关闭','已承接')
   partial=not hard and available>0 and bool(compatible) and (not capacity_ok or not complete) and r.get('status')=='已认证'
   if r.get('status')!='已认证':hard.append('供方资质/资源状态待核验')
   if demand.get('status') in ('已关闭','已承接'):hard.append('需求已关闭或已承接')
   if not modes:hard.append('需求未明确运输方式')
   score=(25*len(compatible)/max(1,len(modes))+25*(min(available/weight,1) if weight else 0)+(20 if r.get('origin')==demand.get('origin') else 10 if r.get('coverage') else 0)+(15 if complete else 6)+(15 if not requires_cold or r.get('coldChain') else 0)) if not hard else 0
   if hard:reasons.extend(hard)
   result.append({**r,'resourceCategory':category,'capacityUnit':r.get('capacityUnit','吨'),'eligible':eligible,'partialMatch':partial,'completeTrip':complete,'matchScore':round(score) if (eligible or partial) else 0,'scope':'整票方式覆盖' if complete else '仅覆盖部分运输段','matchedModes':compatible,'reasons':reasons,'hardGaps':hard,'referenceUnitPrice':r.get('price'),'priceBasis':'演示资源报价参数；实际计价单位、燃油/装卸/附加费和有效期须供需双方确认'})
  else:
   req_area=float(demand.get('storageAreaM2',0) or 0);req_volume=float(demand.get('storageVolumeM3',0) or 0);unit='㎡' if req_area else 'm³' if req_volume else None
   if requires_cold and not r.get('coldChain'):hard.append('需求需要冷链仓储，供给未声明冷库能力')
   if not storage_needed:hard.append('当前需求未填写仓储时长/面积/体积；仓储供给单独展示，不计作运输运力')
   req_capacity=req_area if unit=='㎡' else req_volume if unit=='m³' else 0
   if req_capacity and available<req_capacity:hard.append(f'可用仓储{available:g}{r.get("capacityUnit","㎡")}低于需求{req_capacity:g}{unit}')
   eligible=storage_needed and not hard and r.get('status')=='已认证' and demand.get('status') not in ('已关闭','已承接')
   if r.get('status')!='已认证':hard.append('仓储资质/资源状态待核验')
   if hard:reasons.extend(hard)
   else:reasons.extend(['仓储资源按面积/容积单独匹配','库型、温区、入库时段和装卸能力须逐项确认'])
   result.append({**r,'resourceCategory':category,'capacityUnit':r.get('capacityUnit','㎡'),'eligible':eligible,'partialMatch':False,'completeTrip':False,'matchScore':65 if eligible else 0,'scope':'仓储服务，不替代运输运力','matchedModes':[],'reasons':reasons,'hardGaps':hard,'referenceUnitPrice':r.get('price'),'priceBasis':'演示仓储报价参数；计费单位、仓租周期、装卸费用和温控附加费待双方确认'})
 result.sort(key=lambda x:(x['eligible'],x['partialMatch'],x['matchScore']),reverse=True)
 transport=[x for x in result if x['resourceCategory']=='transport'];warehouses=[x for x in result if x['resourceCategory']=='warehouse']
 return {'demand':demand,'supplies':result,'transportSupplies':transport,'warehouseSupplies':warehouses,'eligibleCount':sum(x['eligible'] for x in result),'partialCount':sum(x['partialMatch'] for x in result),'supplyCount':len(result),'weightTons':weight,'requiredModes':modes,'requiresColdChain':requires_cold,'requiresHazmat':hazardous,'requiresStorage':storage_needed,'simulation':True,'criteria':'先核运输方式、资质、温控/危险品、可用能力及业务状态，再按容量、地点覆盖和完整链路覆盖度评分。运输吨位与仓储面积/容积分别匹配；分段运力显示部分匹配，不冒充整票承运能力。'}
