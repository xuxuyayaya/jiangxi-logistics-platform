"""Candidate intermodal planning. Real provider geometry, explicitly demo commercial offers."""
import concurrent.futures,math,re
from datetime import datetime,timedelta
from route_service import build_route,parse_user_point,NODES,km
from real_routes import apply_real_routes,geocode_place
# Approximate city reference points rank candidates only; actual terminal locations must be geocoded.
TERMINALS={
 '铁路': [('南昌向塘国际陆港',115.927,28.429),('赣州国际陆港',114.788,25.839),('上海芦潮港铁路集装箱中心站',121.85,30.87),('武汉吴家山铁路集装箱中心站',114.12,30.66),('长沙霞凝铁路货场',112.98,28.32),('广州大朗铁路货场',113.24,23.24),('深圳平湖南铁路货场',114.12,22.68),('成都城厢铁路集装箱中心站',104.31,30.88),('重庆团结村铁路集装箱中心站',106.39,29.65),('西安新筑铁路集装箱中心站',109.07,34.38),('郑州圃田铁路集装箱中心站',113.82,34.71),('天津新港北铁路集装箱中心站',117.77,39.04),('昆明王家营西铁路货场',102.85,24.87),('沈阳东铁路货场',123.51,41.85),('长春兴隆山铁路货场',125.46,43.96),('哈尔滨新香坊铁路物流中心',126.77,45.72),('济南董家镇铁路物流基地',117.29,36.78),('乌鲁木齐集装箱中心站',87.43,43.88),('兰州铁路集装箱中心站',103.5,36.1),('南宁国际铁路港',108.2,22.75),('贵阳都拉营铁路货场',106.71,26.73),('合肥北铁路物流基地',117.28,32.01)],
 '水运':[('九江港城西港区',115.926,29.713),('上海外高桥港区',121.59,31.35),('宁波舟山港北仑港区',121.86,29.93),('武汉阳逻港',114.58,30.66),('南京龙潭港',119.06,32.17),('重庆果园港',106.75,29.62),('深圳盐田港',114.27,22.58),('广州南沙港',113.67,22.64),('天津港',117.75,38.99),('大连港大窑湾港区',121.89,38.99),('青岛前湾港',120.21,36.0),('营口鲅鱼圈港',122.09,40.28),('烟台港',121.39,37.57),('日照港',119.54,35.38),('连云港港',119.45,34.75),('福州江阴港',119.29,25.45),('厦门海沧港',118.02,24.46),('湛江港',110.42,21.18),('海口港',110.26,20.03)]}
RIVER_PORTS={'九江港城西港区','武汉阳逻港','南京龙潭港','重庆果园港'}
ESTUARY_PORT='上海外高桥港区'
PROFILES={'公路':('赣通公路物流（演示公司）',.55,420,0),'铁路':('赣通铁路货代（演示公司）',.19,600,22),'水运':('赣通港航物流（演示公司）',.09,900,16)}
def resolve(name):
 p=parse_user_point(name)
 if p:return p
 return list(NODES[name]) if name in NODES else geocode_place(name)
def resolve_terminal(hub):
 name,lon,lat=hub
 p=resolve(name)
 if p and km(p,[lon,lat])<=100:return p
 # A geocoder may return an unrelated business with the same port/station name.
 # Never feed a position outside the terminal's region into routing or pricing.
 return None
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
   notes.append(mode+'未找到两端400公里范围内的不同候选站港，保留端到端查询供核验。');out.append([{**l,'terminalUnverified':True} for l in legs]);continue
  hubs=[start,end]
  # River/coastal services connect via the Yangtze estuary as a proposed interchange,
  # not a claim that a through sailing or a booked transshipment exists.
  if mode=='水运' and ((start[0] in RIVER_PORTS)!=(end[0] in RIVER_PORTS)) and ESTUARY_PORT not in (start[0],end[0]):
   gateway=next(h for h in catalog if h[0]==ESTUARY_PORT);hubs=[start,gateway,end]
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:locations=list(pool.map(resolve_terminal,hubs))
  if not all(locations):
   notes.append(mode+'候选站港定位未完成，未插入未经定位的换装节点。');out.append([{**l,'terminalUnverified':True} for l in legs]);continue
  route=[]
  if origin!=start[0]:route.append({'from':origin,'to':named(start[0],locations[0]),'mode':'公路'})
  for j in range(len(hubs)-1):route.append({'from':named(hubs[j][0],locations[j]),'to':named(hubs[j+1][0],locations[j+1]),'mode':mode})
  if dest!=end[0]:route.append({'from':named(end[0],locations[-1]),'to':dest,'mode':'公路'})
  out.append(route)
 return out,notes

def commercial(route,x):
 w=float(x['weight']);cold=any(k in str(x.get('requirements',''))+str(x.get('cargo','')) for k in ('冷链','冷藏','冷冻'));total=0;complete=True;hours=0;time_complete=True
 for s in route['segments']:
  mode=s['mode'];company,rate,minimum,handling=PROFILES[mode];river=mode=='水运' and any(n in RIVER_PORTS for n in (s['from'],s['to']));service='长江内河运输' if river else '沿海运输' if mode=='水运' else '公路接驳 / 干线' if mode=='公路' else '铁路干线';s['serviceType']=service
  if mode=='水运':company='赣通长江航运（演示公司）' if river else '赣通沿海航运（演示公司）'
  distance=s['distanceKm'];source='线路服务返回里程'
  if distance is None and s.get('fromPoint') and s.get('toPoint'):
   distance=round(km(s['fromPoint'],s['toPoint'])*(1.25 if mode=='公路' else 1.5 if river else 1.15),2);source='按端点球面距离及计费系数估算，仅用于演示报价，不是路径里程'
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
 budget=x.get('budget');route['withinBudget']=None if budget in (None,'') or not complete else total<=float(budget)
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
  r=apply_real_routes(build_route(order,'demands'));r['name']='江海联运（上海中转候选）' if sum(l['mode']=='水运' for l in legs)>1 else '沿海水运' if all(l['mode']=='水运' for l in legs) else '公铁联运' if multi and any(l['mode']=='铁路' for l in legs) else '公水联运' if multi else legs[0]['mode']+'直达';r['intermodalCandidate']=len(set(l['mode'] for l in legs))>1 or sum(l['mode']=='水运' for l in legs)>1;r['waterCandidate']=any(l['mode']=='水运' for l in legs);r['waterNotice']='内河—沿海组合需在上海核验换船、港区作业、箱型、温控及等待时间；未确认班期、舱位或直达航线。' if sum(l['mode']=='水运' for l in legs)>1 else '港口间沿海运输候选，需确认班期、舱位、箱型及货类受理。' if r['waterCandidate'] else '';r['nodeBasis']='用户指定分段' if x.get('legs') else '真实站港目录候选，定位已核实；接驳与货运受理仍需确认' if multi else '用户输入起讫地点'
  r['terminalVerified']=not any(l.get('terminalUnverified') for l in legs)
  if r['waterCandidate'] and not r['terminalVerified']:
   r['name']='水运站港待定位'
   for seg in r['segments']:
    if seg['mode']=='水运':seg['routeQuery']={'state':'terminal_unresolved','message':'候选港口定位未完成，不绘制城市间航线。'}
  return commercial(r,x)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:routes=list(pool.map(run,enumerate(sets)))
 eligible=[r for r in routes if (r['routeReady'] or (r['waterCandidate'] and r['terminalVerified'] and all(s['routeQuery']['state']=='ready' or (s['mode']=='水运' and s['routeQuery']['state']=='schematic') for s in r['segments']))) and r['quote']['complete'] and r['withinBudget'] is not False and r['arrivalFeasible'] is not False]
 if eligible:
  preference=x.get('objective','multimodal')
  if preference=='multimodal':
   intermodal=[r for r in eligible if r['intermodalCandidate']]
   if intermodal:eligible=intermodal
  best=min(eligible,key=lambda r:r['serviceHours'] if preference=='fastest' else r['quote']['total'] if preference=='cheapest' else r['quote']['total']*(1+(r['serviceHours'] or 0)/240))
  best['recommendation']={'fastest':'时效优先推荐','cheapest':'费用优先推荐','multimodal':'联运优先推荐'}.get(preference,'综合推荐')
  if preference=='multimodal' and not best['intermodalCandidate']:best['recommendation']='公路 / 单式参照 · 联运条件待核验'
  if best['waterCandidate'] and not best['routeReady']:best['recommendation']=best['recommendation'].replace('推荐','候选')+' · 航线待核验'
 for r in routes:
  if r['withinBudget'] is False:r['recommendation']='超出预算'
  if r['arrivalFeasible'] is False:r['recommendation']='到达时限存在风险'
 routes.sort(key=lambda r:(not r['intermodalCandidate'],not r['quote']['complete']))
 return {'plans':routes,'planningNotes':notes,'orderTemplate':{k:v for k,v in routes[0]['order'].items() if k not in ('id','created')},'notice':'推荐节点来自真实站港目录并经定位，属于待确认候选；线路几何来自对应路径服务。公司、价格和运营时效为演示测算，非真实承运报价。未取得线路时不伪造路径，缺失计费条件时不生成总价。'}
