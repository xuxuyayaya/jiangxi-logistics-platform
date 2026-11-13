import sys,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
import planner_service as p,real_routes
LOC={'南昌市':[115.85,28.68],'上海市':[121.47,31.23],'深圳市':[114.06,22.55],'上海芦潮港铁路集装箱中心站':[121.85,30.87],'深圳平湖南铁路货场':[114.12,22.68]}
def route(a,b):return {'state':'ready','geometry':[a,b],'distanceKm':round(p.km(a,b)*1.3,2),'durationHours':5,'source':'test provider','coordinateSystem':'WGS84','message':'test fixture'}
class PlannerTests(unittest.TestCase):
 def setUp(self):
  self.patchers=[patch.object(p,'geocode_place',side_effect=lambda n:LOC.get(n)),patch.object(real_routes,'geocode_place',side_effect=lambda n:LOC.get(n)),patch.object(real_routes,'route_road',side_effect=route),patch.object(real_routes,'route_rail',side_effect=route)]
  for q in self.patchers:q.start();self.addCleanup(q.stop)
 def solve(self,dest='上海市',weight=20):
  x={'origin':'南昌市','destination':dest,'weight':weight,'cargo':'家具','objective':'cheapest','budget':999999}
  sets=[[{'from':x['origin'],'to':dest,'mode':m}] for m in ['公路','铁路']]
  return p.solve(x,sets)
 def test_auto_nodes_prices_and_endpoint_change(self):
  a=self.solve();rail=next(r for r in a['plans'] if r['name']=='公铁联运');self.assertEqual([s['mode'] for s in rail['segments']],['公路','铁路','公路']);self.assertEqual(rail['points'][1]['name'],'南昌向塘国际陆港');self.assertEqual(rail['points'][-2]['name'],'上海芦潮港铁路集装箱中心站')
  for r in a['plans']:
   self.assertAlmostEqual(r['quote']['total'],sum(s['quote']['total'] for s in r['segments']),places=2)
   self.assertTrue(all('演示公司' in s['carrier'] for s in r['segments']))
  b=self.solve('深圳市');self.assertEqual(next(r for r in b['plans'] if r['name']=='公铁联运')['points'][-2]['name'],'深圳平湖南铁路货场');self.assertNotEqual(next(r for r in a['plans'] if r['name']=='公路直达')['quote']['total'],next(r for r in b['plans'] if r['name']=='公路直达')['quote']['total']);self.assertGreater(next(r for r in self.solve(weight=40)['plans'] if r['name']=='公路直达')['quote']['total'],next(r for r in a['plans'] if r['name']=='公路直达')['quote']['total'])
 def test_missing_path_no_fabricated_geometry(self):
  with patch.object(real_routes,'route_rail',return_value={'state':'no_route','message':'no coverage'}):
   r=next(r for r in self.solve()['plans'] if r['name']=='公铁联运');self.assertFalse(r['routeReady']);self.assertEqual(r['segments'][1]['geometry'],[]);self.assertIsNotNone(r['quote']['total']);self.assertIn('估算',r['segments'][1]['quote']['distanceSource'])
 def test_unknown_location_no_price(self):
  r=next(r for r in self.solve('未知地区')['plans'] if r['name']=='公路直达');self.assertIsNone(r['quote']['total']);self.assertFalse(r['routeReady'])
 def test_default_prefers_intermodal_even_when_road_cheaper(self):
  original=p.commercial
  def price(r,x):
   r=original(r,x);r['quote']['total']=1000 if r['intermodalCandidate'] else 100;return r
  x={'origin':'南昌市','destination':'上海市','weight':20}
  with patch.object(p,'commercial',side_effect=price):
   result=p.solve(x,[[{'from':x['origin'],'to':x['destination'],'mode':m}] for m in ['公路','铁路']])
  self.assertTrue(result['plans'][0]['intermodalCandidate']);self.assertEqual(result['plans'][0]['recommendation'],'联运优先推荐')
 def test_manual_leg_preserved(self):
  legs=[{'from':'南昌市','to':'上海市','mode':'公路'}];x={'origin':'南昌市','destination':'上海市','weight':20,'legs':legs};self.assertEqual(p.recommend_sets(x,[legs])[0],[legs])
class WaterPlanningTests(unittest.TestCase):
 def setUp(self):
  self.locations={'天津市':[117.2,39.12],'大连市':[121.61,38.91],'九江市':[115.99,29.71],'天津港':[117.75,38.99],'大连港大窑湾港区':[121.89,38.99],'上海外高桥港区':[121.59,31.35],'上海市':[121.47,31.23]}
  for q in [patch.object(p,'geocode_place',side_effect=self.locations.get),patch.object(real_routes,'geocode_place',side_effect=self.locations.get),patch.object(real_routes,'route_road',side_effect=route)]:q.start();self.addCleanup(q.stop)
 def solve(self,a,b):
  return p.solve({'origin':a,'destination':b,'weight':20,'objective':'cheapest'},[[{'from':a,'to':b,'mode':m}] for m in ['公路','水运']])
 def test_tianjin_dalian_coastal_candidate(self):
  r=next(r for r in self.solve('天津市','大连市')['plans'] if r['waterCandidate']);water=[s for s in r['segments'] if s['mode']=='水运'];self.assertEqual(len(water),1);self.assertEqual((water[0]['from'],water[0]['to']),('天津港','大连港大窑湾港区'));self.assertEqual(water[0]['serviceType'],'沿海运输');self.assertIn('候选',r['recommendation']);self.assertFalse(r['routeReady']);self.assertEqual(water[0]['geometry'],[])
 def test_jiujiang_dalian_yangtze_gateway(self):
  for a,b,ports in [('九江市','大连市',['九江港城西港区','上海外高桥港区','大连港大窑湾港区']),('大连市','九江市',['大连港大窑湾港区','上海外高桥港区','九江港城西港区'])]:
   r=next(r for r in self.solve(a,b)['plans'] if r['waterCandidate']);water=[s for s in r['segments'] if s['mode']=='水运'];self.assertEqual([water[0]['from']]+[s['to'] for s in water],ports);self.assertEqual(len(water),2);self.assertAlmostEqual(r['quote']['total'],sum(s['quote']['total'] for s in r['segments']),2);self.assertIn('上海中转',r['name']);self.assertTrue(all(s['routeQuery']['state']=='schematic' for s in water))
 def test_wrong_region_port_is_rejected(self):
  self.locations['天津港']=[87.6,43.8]
  r=self.solve('天津市','大连市')
  self.assertTrue(any('定位未完成' in n for n in r['planningNotes']))
  self.assertFalse(any(pnt['name']=='天津港' for plan in r['plans'] for pnt in plan['points']))
 def test_shanghai_not_inserted_twice(self):
  r=next(r for r in self.solve('九江市','上海市')['plans'] if r['waterCandidate']);self.assertEqual(len([s for s in r['segments'] if s['mode']=='水运']),1)
if __name__=='__main__':unittest.main()
