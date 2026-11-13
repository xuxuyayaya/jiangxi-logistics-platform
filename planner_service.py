"""Candidate intermodal planning. Real provider geometry, explicitly demo commercial offers."""
import concurrent.futures,math,re
from datetime import datetime,timedelta
from route_service import build_route,parse_user_point,NODES,km
from real_routes import apply_real_routes,geocode_place
# Approximate city reference points rank candidates only; actual terminal locations must be geocoded.
TERMINALS={
 '铁路': [('南昌向塘国际陆港',115.927,28.429),('赣州国际陆港',114.788,25.839),('上海芦潮港铁路集装箱中心站',121.85,30.87),('武汉吴家山铁路集装箱中心站',114.12,30.66),('长沙霞凝铁路货场',112.98,28.32),('广州大朗铁路货场',113.24,23.24),('深圳平湖南铁路货场',114.12,22.68),('成都城厢铁路集装箱中心站',104.31,30.88),('重庆团结村铁路集装箱中心站',106.39,29.65),('西安新筑铁路集装箱中心站',109.07,34.38),('郑州圃田铁路集装箱中心站',113.82,34.71),('天津新港北铁路集装箱中心站',117.77,39.04),('昆明王家营西铁路货场',102.85,24.87)],
 '水运':[('九江港城西港区',115.926,29.713),('上海外高桥港区',121.59,31.35),('宁波舟山港北仑港区',121.86,29.93),('武汉阳逻港',114.58,30.66),('南京龙潭港',119.06,32.17),('重庆果园港',106.75,29.62),('深圳盐田港',114.27,22.58),('广州南沙港',113.67,22.64),('天津港',117.75,38.99),('青岛前湾港',120.21,36.0)]}
PROFILES={'公路':('赣通公路物流（演示公司）',.55,420,0),'铁路':('赣通铁路货代（演示公司）',.19,600,22),'水运':('赣通港航物流（演示公司）',.09,900,16)}
def resolve(name):
 p=parse_user_point(name)
 if p:return p
 return list(NODES[name]) if name in NODES else geocode_place(name)
def named(name,p):return name+f'[{p[0]},{p[1]}]'
def recommend_sets(x,sets):
 origin,dest=str(x['origin']).strip(),str(x['destination']).strip()
 if x.get('legs') or x.get('autoTransfer') is False:return sets,[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(resolve,[origin,dest]))
 notes=[];out=[]
 for legs in sets:
  mode=legs[0]['mode']
  if mode=='公路' or not a or not b:out.append(legs);continue
  catalog=TERMINALS[mode]
  start=min(catalog,key=lambda h:km(a,h[1:]));end=min(catalog,key=lambda h:km(b,h[1:]))
  if start==end or km(a,start[1:])>400 or km(b,end[1:])>400:
   notes.append(mode+'未找到两端400公里范围内的不同候选站港，保留端到端查询供核验。');out.append(legs);continue
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:sp,ep=list(pool.map(resolve,[start[0],end[0]]))
  if not sp or not ep:
   notes.append(mode+'候选站港定位未完成，未插入未经定位的换装节点。');out.append(legs);continue
  route=[]
  if origin!=start[0]:route.append({'from':origin,'to':named(start[0],sp),'mode':'公路'})
  route.append({'from':named(start[0],sp),'to':named(end[0],ep),'mode':mode})
  if dest!=end[0]:route.append({'from':named(end[0],ep),'to':dest,'mode':'公路'})
  out.append(route)
 return out,notes

def commercial(route,x):
 w=float(x['weight']);cold=any(k in str(x.get('requirements',''))+str(x.get('cargo','')) for k in ('冷链','冷藏','冷冻'));total=0;complete=True;hours=0;time_complete=True
 for s in route['segments']:
  mode=s['mode'];company,rate,minimum,handling=PROFILES[mode];distance=s['distanceKm'];source='线路服务返回里程'
  if distance is None and s.get('fromPoint') and s.get('toPoint'):
   distance=round(km(s['fromPoint'],s['toPoint'])*(1.25 if mode=='公路' else 1.15),2);source='按端点球面距离及计费系数估算，仅用于演示报价，不是路径里程'
  factor=1.25 if cold and mode=='公路' else 1
  freight=round(max(minimum, w*distance*rate)*factor,2) if distance is not None else None
  transfer=round(w*handling,2);road_toll=s.get('routeQuery',{}).get('toll');toll=round(road_toll*math.ceil(w/32),2) if mode=='公路' and road_toll is not None else None
  amount=round(freight+transfer+(toll or 0),2) if freight is not None else None
  s.update(carrier=company,carrierStatus='演示候选，未确认承运',quote={'currency':'CNY','type':'演示测算','freight':freight,'handling':transfer,'toll':toll,'total':amount,'billingDistanceKm':distance,'distanceSource':source,'ratePerTonKm':rate,'minimumCharge':minimum,'coldMultiplier':factor,'basis':f'运输费=max({minimum}元, 重量×计费距离×{rate}元/吨公里)×温控系数{factor}；装卸换装={handling}元/吨；道路通行费按32吨/车折算，高德未返回时待核验。','exclusions':'不含税、保险、报关及仓储；非承运企业正式报价。'})
  total+=amount or 0;complete=complete and amount is not None
  if distance is not None:
   # Freight operational estimate, not rail router's track travel time.
   h=distance/({'公路':55,'铁路':35,'水运':18}[mode])+({'公路':2,'铁路':12,'水运':18}[mode]);hours+=h
  else:time_complete=False
 route['quote']={'currency':'CNY','total':round(total,2) if complete else None,'knownSubtotal':round(total,2),'type':'演示费用测算，非真实报价','complete':complete,'exclusions':'不含税、保险、报关及仓储；班期、舱位和承运能力未确认。'}
 route['serviceHours']=round(hours,1) if time_complete else None
 route['timeBasis']='按分段计费距离/参考运营速度及作业等待测算，不含已确认班期；不作交付承诺。'
 budget=x.get('budget');route['withinBudget']=None if not budget or not complete else total<=float(budget)
 route['arrivalFeasible']=None
 if x.get('requiredArrival') and x.get('plannedDeparture') and time_complete:
  route['arrivalFeasible']=datetime.fromisoformat(x['plannedDeparture'])+timedelta(hours=hours)<=datetime.fromisoformat(x['requiredArrival'])+timedelta(days=1)
 route['candidateOnly']=not route['routeReady'];route['recommendation']='路径待核验' if not route['routeReady'] else '可比较方案'
 return route

def solve(x,mode_sets):
 sets,notes=recommend_sets(x,mode_sets)
 if x.get('compareRoad') and x.get('legs') and (len(sets[0])>1 or sets[0][0]['mode']!='公路'):sets.append([{'from':x['origin'],'to':x['destination'],'mode':'公路'}])
 def run(item):
  ix,legs=item
  def endpoint(s):return re.sub(r'\s*\[[^]]+\]','',s).strip(),parse_user_point(s)
  origin,oc=endpoint(legs[0]['from']);dest,dc=endpoint(legs[-1]['to']);multi=len(legs)>1
  order={'id':f'QUERY-PLAN-{ix+1}','origin':origin,'destination':dest,'weight':float(x['weight']),'cargo':str(x.get('cargo',''))[:200],'mode':'多式联运' if multi else legs[0]['mode']+'运输','routeModes':','.join(l['mode'] for l in legs),'routeNodes':';'.join(l['to'] for l in legs[:-1]),'title':'运输方案推荐','created':datetime.now().isoformat(timespec='seconds')}
  order.update({k:x[k] for k in ('loadType','plannedDeparture','requiredArrival','budget','requirements') if x.get(k) not in (None,'')})
  if oc:order['originCoords']=','.join(map(str,oc))
  if dc:order['destinationCoords']=','.join(map(str,dc))
  r=apply_real_routes(build_route(order,'demands'));r['name']='公铁联运' if multi and any(l['mode']=='铁路' for l in legs) else '公水联运' if multi else legs[0]['mode']+'直达';r['nodeBasis']='用户指定分段' if x.get('legs') else '真实站港目录候选，定位已核实；接驳与货运受理仍需确认' if multi else '用户输入起讫地点'
  return commercial(r,x)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:routes=list(pool.map(run,enumerate(sets)))
 eligible=[r for r in routes if r['routeReady'] and r['quote']['complete'] and r['withinBudget'] is not False and r['arrivalFeasible'] is not False]
 if eligible:
  preference=x.get('objective','balanced')
  best=min(eligible,key=lambda r:r['serviceHours'] if preference=='fastest' else r['quote']['total'] if preference=='cheapest' else r['quote']['total']*(1+(r['serviceHours'] or 0)/240))
  best['recommendation']={'fastest':'时效优先推荐','cheapest':'费用优先推荐'}.get(preference,'综合推荐')
 for r in routes:
  if r['withinBudget'] is False:r['recommendation']='超出预算'
  if r['arrivalFeasible'] is False:r['recommendation']='到达时限存在风险'
 return {'plans':routes,'planningNotes':notes,'orderTemplate':{k:v for k,v in routes[0]['order'].items() if k not in ('id','created')},'notice':'推荐节点来自真实站港目录并经定位，属于待确认候选；线路几何来自对应路径服务。公司、价格和运营时效为演示测算，非真实承运报价。未取得线路时不伪造路径，缺失计费条件时不生成总价。'}
