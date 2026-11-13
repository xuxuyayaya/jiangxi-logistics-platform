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
  a=self.solve();rail=a['plans'][1];self.assertEqual([s['mode'] for s in rail['segments']],['公路','铁路','公路']);self.assertEqual(rail['points'][1]['name'],'南昌向塘国际陆港');self.assertEqual(rail['points'][-2]['name'],'上海芦潮港铁路集装箱中心站')
  for r in a['plans']:
   self.assertAlmostEqual(r['quote']['total'],sum(s['quote']['total'] for s in r['segments']),places=2)
   self.assertTrue(all('演示公司' in s['carrier'] for s in r['segments']))
  b=self.solve('深圳市');self.assertEqual(b['plans'][1]['points'][-2]['name'],'深圳平湖南铁路货场');self.assertNotEqual(a['plans'][0]['quote']['total'],b['plans'][0]['quote']['total']);self.assertGreater(self.solve(weight=40)['plans'][0]['quote']['total'],a['plans'][0]['quote']['total'])
 def test_missing_path_no_fabricated_geometry(self):
  with patch.object(real_routes,'route_rail',return_value={'state':'no_route','message':'no coverage'}):
   r=self.solve()['plans'][1];self.assertFalse(r['routeReady']);self.assertEqual(r['segments'][1]['geometry'],[]);self.assertIsNotNone(r['quote']['total']);self.assertIn('估算',r['segments'][1]['quote']['distanceSource'])
 def test_unknown_location_no_price(self):
  r=self.solve('未知地区')['plans'][0];self.assertIsNone(r['quote']['total']);self.assertFalse(r['routeReady'])
 def test_manual_leg_preserved(self):
  legs=[{'from':'南昌市','to':'上海市','mode':'公路'}];x={'origin':'南昌市','destination':'上海市','weight':20,'legs':legs};self.assertEqual(p.recommend_sets(x,[legs])[0],[legs])
if __name__=='__main__':unittest.main()
