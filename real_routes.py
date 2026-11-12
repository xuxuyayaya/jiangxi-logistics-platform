"""Gaode Web Service road routing. Never synthesize missing route geometry."""
import os,json,urllib.request,urllib.parse,time,math
CACHE={}
GEOCODE_CACHE={}
def geocode_place(name):
 """Resolve user-entered national/international endpoint names when Gaode can locate them."""
 key=os.getenv('AMAP_WEB_SERVICE_KEY','')
 if not key:return None
 name=(name or '').strip()
 if not name:return None
 hit=GEOCODE_CACHE.get(name)
 if hit and time.time()-hit[0]<86400:return hit[1]
 try:
  parts=[x.strip() for x in name.replace('，',',').split(',') if x.strip()]
  addresses=[name]
  if len(parts)>1:addresses.insert(0,parts[0])
  if '洋山' in name:addresses.extend(['洋山深水港','上海洋山港'])
  city=parts[1] if len(parts)>1 else ('上海市' if '洋山' in name or name=='上海港' else '')
  point=None
  for address in dict.fromkeys(addresses):
   query={'key':key,'address':address,'output':'JSON'}
   if city:query['city']=city
   with urllib.request.urlopen('https://restapi.amap.com/v3/geocode/geo?'+urllib.parse.urlencode(query),timeout=8) as res:data=json.load(res)
   geo=data.get('geocodes',[{}])[0].get('location') if data.get('status')=='1' and data.get('geocodes') else None
   if geo:point=list(map(float,geo.split(',')));break
  GEOCODE_CACHE[name]=(time.time(),point)
  return point
 except Exception:return None
def route_road(a,b):
 key=os.getenv('AMAP_WEB_SERVICE_KEY','')
 if not key:return {'state':'key_required','message':'尚未配置高德Web服务Key（AMAP_WEB_SERVICE_KEY），不能查询真实道路路线。'}
 ck=(tuple(a),tuple(b));hit=CACHE.get(ck)
 if hit and time.time()-hit[0]<1800:return hit[1]
 params={'key':key,'origin':','.join(map(str,a)),'destination':','.join(map(str,b)),'show_fields':'cost,polyline','strategy':'32'}
 try:
  convert={'key':key,'locations':','.join(map(str,a))+';'+','.join(map(str,b)),'coordsys':'gps'}
  with urllib.request.urlopen('https://restapi.amap.com/v3/assistant/coordinate/convert?'+urllib.parse.urlencode(convert),timeout=8) as res:converted=json.load(res)
  if converted.get('status')!='1':return {'state':'provider_error','message':'高德坐标转换失败：'+str(converted.get('info','授权或Key异常'))}
  coords=converted['locations'].split(';');params['origin']=coords[0];params['destination']=coords[1]
  with urllib.request.urlopen('https://restapi.amap.com/v5/direction/driving?'+urllib.parse.urlencode(params),timeout=12) as res:data=json.load(res)
  if data.get('status')!='1':return {'state':'provider_error','message':'高德路线服务返回：'+str(data.get('info','查询失败')),'code':data.get('infocode')}
  paths=data.get('route',{}).get('paths',[])
  if not paths:return {'state':'no_route','message':'高德未返回可用道路路线。'}
  p=paths[0];geo=[];roads=[]
  for st in p.get('steps',[]):
   for pt in st.get('polyline','').split(';'):
    if not pt:continue
    lon,lat=map(float,pt.split(','));geo.append([lon,lat])
   roads.append({'road':st.get('road','未命名道路'),'instruction':st.get('instruction',''),'distanceMeters':float(st.get('step_distance',st.get('distance',0)) or 0)})
  cost=p.get('cost',{});x={'state':'ready','geometry':geo,'distanceKm':round(float(p.get('distance',0))/1000,2),'durationHours':round(float(cost.get('duration',0))/3600,2),'toll':float(cost.get('tolls',0) or 0),'roads':roads,'source':'高德驾车路径规划V5','coordinateSystem':'GCJ02','queriedAt':time.strftime('%Y-%m-%d %H:%M:%S'),'message':'高德道路规划参考，非实时车辆轨迹，也非货车通行许可。'}
  CACHE[ck]=(time.time(),x);return x
 except Exception:return {'state':'request_failed','message':'高德路线查询失败或超时，请检查网络与服务授权。'}
def apply_real_routes(r):
 import concurrent.futures
 # Local hubs have verified coordinates. Resolve free-text endpoints rather than
 # silently routing an unknown city from the default Jiangxi hub.
 pts=r.get('points',[])
 for idx,p in enumerate(pts):
  name=p.get('name')
  if not name or p.get('coordSource')=='user':continue
  known=any(name==n for n in ('南昌向塘国际陆港','九江港城西港区','赣州国际陆港','宜春冷链集配中心','上饶铁路物流园','吉安港物流枢纽','南昌铁路物流中心','九江铁路货场','樟树中转枢纽','鹰潭铁路中转场','吉安铁路货场','赣州铁路货场','丰城港换装码头','万载公路中转站','弋阳公路服务节点'))
  if not known:
   resolved=geocode_place(name)
   if resolved:pts[idx]['point']=resolved;pts[idx]['geocodeState']='resolved'
   else:pts[idx]['point']=None;pts[idx]['geocodeState']='unresolved'
 for i,s in enumerate(r.get('segments',[])):
  if i<len(pts)-1:s['fromPoint']=pts[i]['point'];s['toPoint']=pts[i+1]['point']
 unresolved=any(p.get('geocodeState')=='unresolved' for p in pts)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  jobs={i:pool.submit(route_road,s['fromPoint'],s['toPoint']) for i,s in enumerate(r['segments']) if s['mode']=='公路' and s['fromPoint'] and s['toPoint']}
  for i,s in enumerate(r['segments']):
   s['simulationEstimate']={'distanceKm':s['distanceKm'],'durationHours':s['durationHours']}
   q=jobs[i].result() if i in jobs else {'state':'place_unresolved','message':'高德未能核实本段起讫地名；请补充“城市，省/国家”后重试。'} if s['mode']=='公路' else {'state':'unsupported_mode','message':s['mode']+'货运线路须接入铁路／港航线路数据；高德驾车路线不能代替。'}
   s.update(routeQuery=q,geometry=q.get('geometry',[]),distanceKm=q.get('distanceKm'),durationHours=q.get('durationHours'),coordinateSystem=q.get('coordinateSystem','GCJ02'))
 r['track']=[];r['position']=None;r['coordinateSystem']='GCJ02';r['realRoadRouteCount']=sum(s['routeQuery']['state']=='ready' for s in r['segments']);r['routeReady']=r['realRoadRouteCount']==len(r['segments']);r['totalDistanceKm']=round(sum(s['distanceKm'] or 0 for s in r['segments']),2) if r['routeReady'] else None;r['estimatedDurationHours']=round(sum(s['durationHours'] or 0 for s in r['segments']),2) if r['routeReady'] else None
 r['notice']='道路分段只显示高德返回的真实路网规划线；无Key、查询失败、铁路或水运线路未接入时不绘制替代连线。订单及货量、费用、载具、进度仍为模拟；道路规划不是GPS实测轨迹。'
 return r
