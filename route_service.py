"""Deterministic, explicitly simulated per-order multimodal route data."""
import math,re,hashlib
from datetime import datetime,timedelta
from fastapi import HTTPException,Request
NODES={
 '南昌向塘国际陆港':(115.927,28.429),'九江港城西港区':(115.926,29.713),'赣州国际陆港':(114.788,25.839),
 '宜春冷链集配中心':(114.401,27.804),'上饶铁路物流园':(117.98,28.448),'吉安港物流枢纽':(114.998,27.115),
 '南昌铁路物流中心':(115.884,28.538),'九江铁路货场':(115.944,29.641),'樟树中转枢纽':(115.546,28.055),
 '鹰潭铁路中转场':(117.034,28.238),'吉安铁路货场':(115.028,27.139),'赣州铁路货场':(114.901,25.831),
 '丰城港换装码头':(115.771,28.187),'万载公路中转站':(114.445,28.106),'弋阳公路服务节点':(117.447,28.388)}
def point(name):
 if name in NODES:return list(NODES[name]),True
 for k,v in NODES.items():
  if name and name[:2]==k[:2]:return list(v),True
 return [115.927,28.429],False

def parse_user_point(value):
 """Accept optional WGS84 coordinates in user-entered node fields."""
 m=re.search(r'\[\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*\]',str(value or ''))
 if not m:return None
 try:
  lon,lat=map(float,m.groups())
  return [lon,lat] if -180<=lon<=180 and -90<=lat<=90 else None
 except ValueError:return None

def km(a,b):
 lon1,lat1,lon2,lat2=map(math.radians,(*a,*b));dlon=lon2-lon1;dlat=lat2-lat1;return 6371*2*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))
def build_route(x,kind):
 """Build only the endpoints and explicitly specified waypoints of this order."""
 seed=int(hashlib.sha256(x['id'].encode()).hexdigest()[:8],16)
 mode=x.get('mode','公路运输');origin=x.get('origin','待核实起点');dest=x.get('destination','待核实终点')
 a,ak=point(origin);b,bk=point(dest);manual_indices=set()
 for idx,key in ((0,'originCoords'),(1,'destinationCoords')):
  coord=parse_user_point('['+str(x.get(key,''))+']')
  if coord:
   if idx==0:a,ak=coord,True
   else:b,bk=coord,True
 points=[(origin,a),(dest,b)]
 via=[n.strip() for n in re.split(r'[;；\n]+',str(x.get('routeNodes',''))) if n.strip()]
 if via:
  via_points=[]
  for n in via:
   coord=parse_user_point(n);name=re.sub(r'\s*\[\s*-?\d+(?:\.\d+)?\s*[,，]\s*-?\d+(?:\.\d+)?\s*\]','',n).strip()
   via_points.append((name,coord or point(name)[0]))
   if coord:manual_indices.add(len(via_points))
  points=[(origin,a)]+via_points+[(dest,b)]
 for index,key in ((0,'originCoords'),(len(points)-1,'destinationCoords')):
  coord=parse_user_point('['+str(x.get(key,''))+']')
  if coord:points[index]=(points[index][0],coord);manual_indices.add(index)

 normalize={'水路':'水运','海运':'水运','内河航运':'水运','水路运输':'水运','水运运输':'水运','铁路运输':'铁路','公路运输':'公路','航空运输':'航空'}
 provided=[normalize.get(v.strip(),v.strip()) for v in re.split(r'[;,，；]+',str(x.get('routeModes',''))) if v.strip()]
 base_mode=normalize.get(str(mode).strip(),str(mode).strip())
 multi=any(t in str(mode) for t in ('联运','多式','国际'))
 if not provided and not multi:provided=[base_mode]
 config_error=None
 if len(provided)!=len(points)-1:
  if provided:config_error=f'已填写{len(provided)}个运输段，当前路线包含{len(points)-1}段；请按途经节点补齐运输方式。'
  elif multi:config_error='多式联运需要明确每段实际起讫节点和运输方式；平台不会自动插入中转节点。'
  segment_modes=['待补充实际路线']*(len(points)-1)
 else:segment_modes=provided
 isway=kind=='waybills';progress=max(0,min(100,float(x.get('progress',0) or 0))) if isway else 0;status=x.get('status','待响应')
 started=datetime.fromisoformat(x.get('created',datetime.now().isoformat()))-timedelta(hours=36)
 segments=[];events=[]
 for i,((n1,p1),(n2,p2)) in enumerate(zip(points,points[1:])):
  transport=segment_modes[i]
  sstate='已完成' if isway and progress>=(i+1)/len(points)*100 else '执行中' if isway and progress>i/len(points)*100 else '待执行' if isway else '待承接'
  segments.append({'id':f'{x["id"]}-S{i+1}','index':i,'mode':transport,'from':n1,'to':n2,'fromPoint':p1,'toPoint':p2,'distanceKm':None,'durationHours':None,'status':sstate,'progress':0,'carrier':'待承运方确认','vehicle':'待接入','driver':'待接入','phone':'','plannedDeparture':None,'plannedArrival':None,'geometry':[],'notice':'线路只采用对应路径服务返回的实际路线；未查询到路线时不绘制连接线。'})
 for leg in segments:
  leg['vehicleCount']=None;leg['vehicles']=[]
  leg['vehicleNotice']='运载工具及配载信息仅在承运方或业务系统接入后展示。'
 for i,(name,pt) in enumerate(points):
  done=isway and i/ max(1,len(points)-1)*100 <= progress and progress>0
  events.append({'id':f'EVT-{seed%10000}-{i}','nodeIndex':i,'name':name,'point':pt,'event':'起运节点' if i==0 else '目的节点' if i==len(points)-1 else '用户指定途经节点','plannedTime':None,'actualTime':None,'status':'待真实事件接入' if not done else '待核验业务回执','operator':'待接入','source':'运单事件待接入','remark':'该节点来自订单起讫地或用户指定途经点，不代表实际交接已发生。'})
 weight=float(x.get('weight',100) or 100);cost=float(x.get('price',0) or 0)
 costs=[{'name':n,'amount':None,'basis':'待承运方报价/结算数据接入'} for n in ('干线运输费','短驳接驳费','装卸与换装费','综合协同服务费')]
 alerts=[{'id':'RISK-'+str(seed%10000),'title':'模拟节点滞留核查','level':'中','status':'处理中','node':points[-1][0],'description':'示例运输异常，请按真实业务和设备证据核验。'}] if isway and status=='异常' else []
 docs=[{'id':f'{x["id"]}-{code}','name':name,'status':'演示占位／待真实文件','type':'单据待接入','generated':False} for code,name in [('WB','多式联运电子运单'),('OUT','货物出库交接单'),('CHANGE','换装交接记录'),('RECEIPT','目的站签收回单')]]
 result={'order':x,'kind':kind,'routeId':'ROUTE-'+x['id'],'simulation':True,'coordinateSystem':'WGS84','coordinateVerified':ak and bk,'mode':mode,'progress':progress,'totalDistanceKm':None,'estimatedDurationHours':None,'plannedStart':None,'plannedArrival':None,'points':[{'name':n,'point':pt,'coordSource':'user' if i in manual_indices or (i==0 and x.get('originCoords')) or (i==len(points)-1 and x.get('destinationCoords')) else 'lookup','type':'起点' if i==0 else '终点' if i==len(points)-1 else '用户指定途经点','index':i} for i,(n,pt) in enumerate(points)],'segments':segments,'track':[],'position':None,'events':events,'costs':costs,'alerts':alerts,'documents':docs,'totals':{'weightTons':weight,'packages':x.get('packages'),'containerCount':x.get('containers'),'referenceCost':cost or None},'notice':'订单与运单业务数据为演示数据。公路和铁路只采用已接入路径服务的线路；海运未接入时，地图可在两个已定位港口间显示虚线水上示意，不代表实际航道或航程。系统不会自动补入模拟交接点。'}
 if config_error:result['routeConfigError']=config_error
 return result

def register_routes(app,db,user,visible,record):
 @app.get('/api/routes/{kind}/{rid}')
 def route(kind:str,rid:str,req:Request):
  if kind not in ('demands','waybills'):raise HTTPException(404,'此类记录不具备运输路线')
  u=user(req)
  with db() as c:r=c.execute('select * from records where kind=? and id=?',(kind,rid)).fetchone()
  if not r or not visible(u,r):raise HTTPException(404,'订单不存在或无权访问')
  from real_routes import apply_real_routes
  return apply_real_routes(build_route(record(r),kind))
