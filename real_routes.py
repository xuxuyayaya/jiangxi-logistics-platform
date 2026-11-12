"""Provider-backed road, mapped rail and maritime routing. Never invent geometry."""
import os,json,urllib.request,urllib.parse,time,math
CACHE={}
GEOCODE_CACHE={}
RAIL_CACHE={}
SEA_CACHE={}
def gcj02_to_wgs84(point):
 """Invert AMap's GCJ-02 geocoder result for OSM/WGS84 route providers."""
 lon,lat=map(float,point)
 if lon<72.004 or lon>137.8347 or lat<0.8293 or lat>55.8271:return [lon,lat]
 def transform(lon,lat):
  x=lon-105.0;y=lat-35.0
  dlat=-100+2*x+3*y+.2*y*y+.1*x*y+.2*math.sqrt(abs(x))
  dlat+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
  dlat+=(20*math.sin(y*math.pi)+40*math.sin(y/3*math.pi))*2/3
  dlat+=(160*math.sin(y/12*math.pi)+320*math.sin(y*math.pi/30))*2/3
  dlon=300+x+2*y+.1*x*x+.1*x*y+.1*math.sqrt(abs(x))
  dlon+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
  dlon+=(20*math.sin(x*math.pi)+40*math.sin(x/3*math.pi))*2/3
  dlon+=(150*math.sin(x/12*math.pi)+300*math.sin(x/30*math.pi))*2/3
  rad=lat/180*math.pi;magic=1-.00669342162296594323*math.sin(rad)**2;sqrt=math.sqrt(magic)
  dlat=dlat*180/((6335552.717000426/(magic*sqrt))*math.pi)
  dlon=dlon*180/((6378245/sqrt*math.cos(rad))*math.pi)
  return [lon+dlon,lat+dlat]
 guess=[lon,lat]
 for _ in range(3):
  projected=transform(*guess);guess=[guess[0]+lon-projected[0],guess[1]+lat-projected[1]]
 return guess
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
   if geo:point=gcj02_to_wgs84(list(map(float,geo.split(','))));break
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

def route_rail(a,b):
 """OpenRailRouting returns mapped OSM rail-track geometry, not train service data."""
 ck=(tuple(a),tuple(b));hit=RAIL_CACHE.get(ck)
 if hit and time.time()-hit[0]<3600:return hit[1]
 params=[('point',f'{a[1]},{a[0]}'),('point',f'{b[1]},{b[0]}'),('profile','all_tracks_1435'),('points_encoded','false')]
 try:
  req=urllib.request.Request('https://routing.openrailrouting.org/route?'+urllib.parse.urlencode(params),headers={'Accept':'application/json','User-Agent':'JiangxiLogisticsDemo/1.0'})
  with urllib.request.urlopen(req,timeout=18) as res:data=json.load(res)
  paths=data.get('paths') or []
  if not paths:return {'state':'no_route','message':'铁路轨道数据未返回可连接的线路；请核实站点坐标或由铁路承运方提供线路。'}
  p=paths[0];geometry=p.get('points',{}).get('coordinates',[])
  if len(geometry)<2:return {'state':'no_route','message':'铁路服务未返回有效轨道几何。'}
  result={'state':'ready','geometry':geometry,'distanceKm':round(float(p.get('distance',0))/1000,2),'durationHours':round(float(p.get('time',0))/3600000,2),'source':'OpenRailRouting / OpenStreetMap 铁路轨道','coordinateSystem':'WGS84','queriedAt':time.strftime('%Y-%m-%d %H:%M:%S'),'message':'地图几何为已映射铁路轨道规划；不含实际班次、舱位、货运许可或实时列车位置。'}
  RAIL_CACHE[ck]=(time.time(),result);return result
 except urllib.error.HTTPError as e:
  try:info=json.loads(e.read().decode()).get('message','铁路路径不可用')
  except Exception:info='铁路路径服务暂不可用'
  return {'state':'no_route' if 'Connection between locations not found' in info or 'Cannot find point' in info else 'provider_error','message':info+'；当前地图数据覆盖不完整，未绘制替代线。'}
 except Exception:return {'state':'request_failed','message':'铁路轨道服务查询失败或超时。'}

def route_sea(a,b):
 """Searoutes real sea-lane service; requires an account API key configured server-side."""
 key=os.getenv('SEAROUTES_API_KEY','')
 if not key:return {'state':'key_required','message':'水运实线路需要配置 SEAROUTES_API_KEY（Searoutes服务）；未接入前仅展示港口节点，不绘制示意线。'}
 ck=(tuple(a),tuple(b));hit=SEA_CACHE.get(ck)
 if hit and time.time()-hit[0]<3600:return hit[1]
 url='https://api.searoutes.com/route/v2/sea/'+','.join(map(str,a))+'/'+','.join(map(str,b))
 try:
  req=urllib.request.Request(url,headers={'x-api-key':key,'Accept':'application/json','User-Agent':'JiangxiLogisticsDemo/1.0'})
  with urllib.request.urlopen(req,timeout=20) as res:data=json.load(res)
  geom=data.get('geometry') or (data.get('features') or [{}])[0].get('geometry') or {}
  props=data.get('properties') or (data.get('features') or [{}])[0].get('properties') or {}
  coords=geom.get('coordinates') or []
  if len(coords)<2:return {'state':'no_route','message':'港航服务未返回有效海上航线。'}
  dist=props.get(' length') or props.get('length') or props.get('distance')
  if isinstance(dist,dict):dist=dist.get('value')
  duration=props.get('duration')
  if isinstance(duration,dict):duration=duration.get('value')
  result={'state':'ready','geometry':coords,'distanceKm':round(float(dist)/1000,2) if dist else None,'durationHours':round(float(duration)/3600,2) if duration else None,'source':'Searoutes 海上航线规划','coordinateSystem':'WGS84','queriedAt':time.strftime('%Y-%m-%d %H:%M:%S'),'message':'海上航线规划参考，不代表船舶实时轨迹、船期、舱位或通航许可。'}
  SEA_CACHE[ck]=(time.time(),result);return result
 except urllib.error.HTTPError as e:
  return {'state':'provider_error','message':'水运服务查询失败（HTTP '+str(e.code)+'）；请核验Searoutes账号、额度及服务范围。'}
 except Exception:return {'state':'request_failed','message':'水运航线服务查询失败或超时。'}
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
  jobs={i:pool.submit({'公路':route_road,'铁路':route_rail,'水运':route_sea}[s['mode']],s['fromPoint'],s['toPoint']) for i,s in enumerate(r['segments']) if s['mode'] in ('公路','铁路','水运') and s['fromPoint'] and s['toPoint']}
  for i,s in enumerate(r['segments']):
   s['simulationEstimate']={'distanceKm':s['distanceKm'],'durationHours':s['durationHours']}
   q=jobs[i].result() if i in jobs else {'state':'place_unresolved','message':'地图服务未能核实本段起讫地名；请补充“城市，省/国家”后重试。'} if s['mode'] in ('公路','铁路','水运') else {'state':'unsupported_mode','message':s['mode']+'线路暂未接入对应的真实路径服务。'}
   s.update(routeQuery=q,geometry=q.get('geometry',[]),distanceKm=q.get('distanceKm'),durationHours=q.get('durationHours'),coordinateSystem=q.get('coordinateSystem','GCJ02'))
 r['track']=[];r['position']=None;r['coordinateSystem']='WGS84';r['realRoadRouteCount']=sum(s['routeQuery']['state']=='ready' and s['mode']=='公路' for s in r['segments']);r['realRailRouteCount']=sum(s['routeQuery']['state']=='ready' and s['mode']=='铁路' for s in r['segments']);r['realWaterRouteCount']=sum(s['routeQuery']['state']=='ready' and s['mode']=='水运' for s in r['segments']);r['routeReady']=all(s['routeQuery']['state']=='ready' for s in r['segments']);r['totalDistanceKm']=round(sum(s['distanceKm'] or 0 for s in r['segments']),2) if r['routeReady'] else None;r['estimatedDurationHours']=round(sum(s['durationHours'] or 0 for s in r['segments']),2) if r['routeReady'] else None
 r['notice']='道路分段只显示高德返回的真实路网规划线；无Key、查询失败、铁路或水运线路未接入时不绘制替代连线。订单及货量、费用、载具、进度仍为模拟；道路规划不是GPS实测轨迹。'
 return r
