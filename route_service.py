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

def km(a,b):
 lon1,lat1,lon2,lat2=map(math.radians,(*a,*b));dlon=lon2-lon1;dlat=lat2-lat1;return 6371*2*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))
def build_route(x,kind):
 seed=int(hashlib.sha256(x['id'].encode()).hexdigest()[:8],16);mode=x.get('mode','公路运输');origin=x.get('origin','待核实起点');dest=x.get('destination','待核实终点');a,ak=point(origin);b,bk=point(dest)
 # Use real hub coordinates as anchors; links and interpolated points are simulation, not road geometry.
 candidates=['南昌铁路物流中心','樟树中转枢纽','吉安铁路货场','鹰潭铁路中转场'] if '铁' in mode else ['丰城港换装码头','九江铁路货场','樟树中转枢纽'] if '水' in mode else ['弋阳公路服务节点','万载公路中转站','樟树中转枢纽']
 chosen=[]
 direct=max(1,km(a,b))
 for n in sorted(candidates,key=lambda n:km(a,NODES[n])+km(NODES[n],b)):
  c=NODES[n]
  if km(a,c)>5 and km(b,c)>5 and km(a,c)+km(c,b)<direct*2.8+50:chosen.append(n)
  if len(chosen)==(2 if ('铁' in mode or '水' in mode) else 1):break
 if not chosen and direct>10:
  c=[round((a[0]+b[0])/2,6),round((a[1]+b[1])/2,6)];mid='模拟中途交接节点';points=[(origin,a),(mid,c),(dest,b)]
 else:points=[(origin,a)]+[(n,list(NODES[n])) for n in chosen]+[(dest,b)]
 isway=kind=='waybills';progress=float(x.get('progress',0)) if isway else 0;progress=max(0,min(100,progress));status=x.get('status','待响应')
 segments=[];track=[];cumulative=0
 started=datetime.fromisoformat(x.get('created',datetime.now().isoformat()))-timedelta(hours=36)
 for i in range(len(points)-1):
  n1,p1=points[i];n2,p2=points[i+1];transport=('铁路' if '铁' in mode else '水运') if len(points)>3 and i==1 else ('铁路' if '铁' in mode else '水运') if len(points)==3 and i==1 and ('铁' in mode or '水' in mode) else '公路'
  dist=round(km(p1,p2)*(1.2 if transport=='公路' else 1.08),1);duration=round(dist/({'公路':55,'铁路':65,'水运':18}[transport])+(.4 if i==0 else 1.2),1)
  geom=[]
  for j in range(21):
   f=j/20;v=[round(p1[0]+(p2[0]-p1[0])*f,6),round(p1[1]+(p2[1]-p1[1])*f,6)];geom.append(v)
   if i==0 or j>0:track.append({'lng':v[0],'lat':v[1],'segment':i,'fraction':round((i+f)/(len(points)-1),4),'source':'模拟路线采样点'})
  sp=progress/100*(len(points)-1)-i;sstate='已完成' if sp>=1 else '执行中' if sp>0 else '待执行' if isway else '待承接'
  dept=started+timedelta(hours=cumulative);arr=dept+timedelta(hours=duration);cumulative+=duration
  segments.append({'id':f'{x["id"]}-S{i+1}','index':i,'mode':transport,'from':n1,'to':n2,'fromPoint':p1,'toPoint':p2,'distanceKm':dist,'durationHours':duration,'status':sstate,'progress':round(max(0,min(1,sp))*100),'carrier':['赣通公路运输（模拟）','江西干线联运（模拟）','赣运城配服务（模拟）'][i%3],'vehicle':f'赣A·{10000+seed%80000}' if transport=='公路' else f'模拟班列 X{7000+seed%900}' if transport=='铁路' else f'模拟货船 赣航{seed%1000:03}','driver':'模拟驾驶员' if transport=='公路' else '模拟调度员','phone':'138****'+str(seed%10000).zfill(4),'plannedDeparture':dept.isoformat(timespec='minutes'),'plannedArrival':arr.isoformat(timespec='minutes'),'geometry':geom,'notice':'距离、时效、载具及线路均为模拟估值；连接线不代表真实道路或航道。'})
 for leg in segments:
  qty=max(1,math.ceil(float(x.get('weight',100) or 100)/32)) if leg['mode']=='公路' else 1
  leg['vehicleCount']=qty
  leg['vehicles']=[{'number':f'赣A·{10000+(seed+j*37)%80000}' if leg['mode']=='公路' else leg['vehicle'],'cargoTons':round(float(x.get('weight',100) or 100)/qty,3),'status':leg['status'],'source':'模拟载具配载示例'} for j in range(min(qty,100))]
  leg['vehicleNotice']='公路按32吨/车演示估算；车型、核载及真实运输要求须由承运方核验。' if leg['mode']=='公路' else '模拟一项干线运输任务，不代表真实班列、舱位或承载许可。'
 total=sum(s['distanceKm'] for s in segments);idx=min(len(track)-1,round(progress/100*(len(track)-1)));cur=track[idx];events=[]
 for i,(name,pt) in enumerate(points):
  phase=i/(len(points)-1)*100;done=isway and progress>=phase and progress>0;etime=started if i==0 else datetime.fromisoformat(segments[i-1]['plannedArrival'])
  events.append({'id':f'EVT-{seed%10000}-{i}','nodeIndex':i,'name':name,'point':pt,'event':['发运出库','换装交接','目的站签收'][0 if i==0 else 2 if i==len(points)-1 else 1],'plannedTime':etime.isoformat(timespec='minutes'),'actualTime':etime.isoformat(timespec='minutes') if done else None,'status':'已完成' if done else '计划节点','operator':'模拟节点操作员','source':'演示节点事件','remark':'完成状态按模拟运单进度推演，不是真实设备回传。'})
 weight=float(x.get('weight',100) or 100);cost=float(x.get('price',round(total*weight*.42)) or 0);costs=[{'name':n,'amount':round(cost*r,2),'basis':'模拟费用拆分，非结算或开票凭证'} for n,r in [('干线运输费',.68),('短驳接驳费',.18),('装卸与换装费',.09),('综合协同服务费',.05)]]
 alerts=[{'id':'RISK-'+str(seed%10000),'title':'模拟节点滞留核查','level':'中','status':'处理中','node':points[min(cur['segment']+1,len(points)-1)][0],'description':'示例运输异常，请按真实业务和设备证据核验。'}] if isway and status=='异常' else []
 docs=[{'id':f'{x["id"]}-{code}','name':name,'status':'已生成模拟样单' if code=='WB' else '示例占位／待真实文件','type':'模拟单据','generated':code=='WB'} for code,name in [('WB','多式联运电子运单'),('OUT','货物出库交接单'),('CHANGE','换装交接记录'),('RECEIPT','目的站签收回单')]]
 return {'order':x,'kind':kind,'routeId':'ROUTE-'+x['id'],'simulation':True,'coordinateSystem':'WGS84','coordinateVerified':ak and bk,'mode':mode,'progress':progress,'totalDistanceKm':round(total,1),'estimatedDurationHours':round(cumulative,1),'plannedStart':started.isoformat(timespec='minutes'),'plannedArrival':(started+timedelta(hours=cumulative)).isoformat(timespec='minutes'),'points':[{'name':n,'point':pt,'type':'起点' if i==0 else '终点' if i==len(points)-1 else '中转','index':i} for i,(n,pt) in enumerate(points)],'segments':segments,'track':track,'position':cur,'events':events,'costs':costs,'alerts':alerts,'documents':docs,'totals':{'weightTons':weight,'packages':max(1,round(weight*3)),'containerCount':max(1,round(weight/25)),'referenceCost':round(cost,2)},'notice':'订单、节点、线路、坐标采样、车辆、费用和事件均为模拟数据。地图连接线不是经路网计算的真实道路路线；页面不会将其标记为GPS实际轨迹。' }

def register_routes(app,db,user,visible,record):
 @app.get('/api/routes/{kind}/{rid}')
 def route(kind:str,rid:str,req:Request):
  if kind not in ('demands','waybills'):raise HTTPException(404,'此类记录不具备运输路线')
  u=user(req)
  with db() as c:r=c.execute('select * from records where kind=? and id=?',(kind,rid)).fetchone()
  if not r or not visible(u,r):raise HTTPException(404,'订单不存在或无权访问')
  return build_route(record(r),kind)
