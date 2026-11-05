/**
 * SRDP Stage 5 final method QA
 *
 * New outputs only; does not overwrite historical exports.
 * 1) Stage5_QA_City_FVC_8Nodes_30m
 * 2) Stage5_QA_Scale_30_100_250_500m
 * 3) Stage5_QA_Endpoint_Percentiles
 *
 * Core rules copied from the Stage 5 candidate method:
 * - Landsat C2 L2 surface reflectance
 * - QA cloud/cirrus/shadow/snow/saturation mask
 * - seasonal ImageCollection.median()
 * - no adjacent-year fallback
 * - pixelwise FVC, clamped to [0, 1]
 */

var EXPORT_FOLDER = 'Wetland_FVC_QA';
var NODE_YEARS = [1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020];
var SCALE_YEARS = [1985, 2000, 2012, 2013, 2020];
var SCALES = [30, 100, 250, 500];

var china = ee.FeatureCollection('projects/my-project-11626-475607/assets/China');
var gaul = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2');

var SH = ['黄浦区','徐汇区','长宁区','静安区','普陀区','虹口区','杨浦区','闵行区','宝山区','嘉定区','浦东新区','金山区','松江区','青浦区','奉贤区','崇明区'];
var BJ = ['东城区','西城区','朝阳区','丰台区','石景山区','海淀区','门头沟区','房山区','通州区','顺义区','昌平区','大兴区','怀柔区','平谷区','密云区','延庆区'];
var TJ = ['和平区','河东区','河西区','南开区','河北区','红桥区','东丽区','西青区','津南区','北辰区','武清区','宝坻区','滨海新区','宁河区','静海区','蓟州区'];
var YRD_PREF = ['南京市','无锡市','徐州市','常州市','苏州市','南通市','连云港市','淮安市','盐城市','扬州市','镇江市','泰州市','宿迁市','杭州市','宁波市','嘉兴市','湖州市','绍兴市','金华市','舟山市','台州市','温州市','衢州市','丽水市','合肥市','芜湖市','蚌埠市','淮南市','马鞍山市','淮北市','铜陵市','安庆市','黄山市','滁州市','阜阳市','宿州市','六安市','亳州市','池州市','宣城市'];
var HEBEI = ['石家庄市','唐山市','秦皇岛市','邯郸市','邢台市','保定市','张家口市','承德市','沧州市','廊坊市','衡水市'];
var GBA_MAIN = ['广州市','深圳市','珠海市','佛山市','惠州市','东莞市','中山市','江门市','肇庆市'];

function namedUnion(fc, name, region) {
  return ee.Feature(fc.geometry().dissolve(), {name: name, region: region});
}

var yrdPref = china.filter(ee.Filter.inList('name', YRD_PREF)).map(function(f){return f.set('region','YRD');});
var cityYRD = yrdPref.merge(ee.FeatureCollection([namedUnion(china.filter(ee.Filter.inList('name', SH)), '上海市', 'YRD')]));

var hebei = china.filter(ee.Filter.inList('name', HEBEI)).map(function(f){return f.set('region','BTH');});
var cityBTH = hebei.merge(ee.FeatureCollection([
  namedUnion(china.filter(ee.Filter.inList('name', BJ)), '北京市', 'BTH'),
  namedUnion(china.filter(ee.Filter.inList('name', TJ)), '天津市', 'BTH')
]));

var mainland = china.filter(ee.Filter.inList('name', GBA_MAIN)).map(function(f){return f.set('region','GBA');});
var hk = gaul.filter(ee.Filter.eq('ADM0_NAME','Hong Kong')).map(function(f){return ee.Feature(f.geometry(),{name:'香港',region:'GBA'});});
var mo = gaul.filter(ee.Filter.eq('ADM0_NAME','Macao')).map(function(f){return ee.Feature(f.geometry(),{name:'澳门',region:'GBA'});});
var cityGBA = mainland.merge(hk).merge(mo);

var annual = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual').mosaic();
var five = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/five-years-map').mosaic();
var WET = [181,182,183,184,185,186,187];

function lcAt(y) {
  var epoch = y < 1988 ? 1985 : (y < 1993 ? 1990 : 1995);
  return y < 2000 ? five.select('b' + (1 + (epoch - 1985) / 5)) : annual.select('b' + (y - 1999));
}
function wetAt(y) { return lcAt(y).remap(WET, ee.List.repeat(1,WET.length), 0).eq(1); }

function prep(img, is8) {
  var q = img.select('QA_PIXEL');
  var ok = q.bitwiseAnd(1).eq(0).and(q.bitwiseAnd(2).eq(0)).and(q.bitwiseAnd(4).eq(0))
    .and(q.bitwiseAnd(8).eq(0)).and(q.bitwiseAnd(16).eq(0)).and(q.bitwiseAnd(32).eq(0))
    .and(img.select('QA_RADSAT').eq(0));
  var red = img.select(is8 ? 'SR_B4' : 'SR_B3').multiply(0.0000275).subtract(0.2);
  var nir = img.select(is8 ? 'SR_B5' : 'SR_B4').multiply(0.0000275).subtract(0.2);
  var den = red.add(nir);
  ok = ok.and(red.gte(0)).and(nir.gte(0)).and(red.lte(1)).and(nir.lte(1)).and(den.gt(1e-6));
  return nir.subtract(red).divide(den).rename('NDVI').updateMask(ok).copyProperties(img,['system:time_start']);
}

function landsat(roi, y, sm, em) {
  var start=ee.Date.fromYMD(y,sm,1), end=ee.Date.fromYMD(y,em,1).advance(1,'month');
  function get(id,is8){return ee.ImageCollection(id).filterBounds(roi).filterDate(start,end).map(function(im){return prep(im,is8);});}
  return y < 2013 ? get('LANDSAT/LT05/C02/T1_L2',false).merge(get('LANDSAT/LE07/C02/T1_L2',false)) : get('LANDSAT/LC08/C02/T1_L2',true);
}

var CFG = [
  {id:'YRD',cities:cityYRD,sm:5,em:10,soil:0.0905,veg:0.7897},
  {id:'GBA',cities:cityGBA,sm:4,em:11,soil:0.1351,veg:0.7911},
  {id:'BTH',cities:cityBTH,sm:5,em:9,soil:0.2080,veg:0.7539}
];
var empty=ee.Image.constant(0).rename('NDVI').updateMask(ee.Image.constant(0));

function annualImages(c,y) {
  var roi=c.cities.geometry().dissolve(), coll=landsat(roi,y,c.sm,c.em), n=coll.size();
  var ndvi=ee.Image(ee.Algorithms.If(n.gt(0),coll.median(),empty)).rename('NDVI');
  var fvc=ndvi.subtract(c.soil).divide(c.veg-c.soil).clamp(0,1).rename('FVC');
  return {roi:roi,coll:coll,n:n,ndvi:ndvi,fvc:fvc,wet:wetAt(y).selfMask()};
}

// 1. Stage 5 city statistics at native Landsat scale.
var cityRows=[];
CFG.forEach(function(c){
  NODE_YEARS.forEach(function(y){
    var z=annualImages(c,y), target=z.fvc.updateMask(z.wet), area=ee.Image.pixelArea().divide(1e6);
    var stack=ee.Image.cat([
      area.updateMask(z.wet).rename('wetland_area_km2'),
      area.updateMask(target.mask()).rename('valid_area_km2'),
      target.multiply(area).rename('fvc_x_area')
    ]);
    var fc=stack.reduceRegions({collection:c.cities,reducer:ee.Reducer.sum(),scale:30,tileScale:8}).map(function(f){
      var total=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(f.get('wetland_area_km2'),null),0,f.get('wetland_area_km2')));
      var valid=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(f.get('valid_area_km2'),null),0,f.get('valid_area_km2')));
      var weighted=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(f.get('fvc_x_area'),null),0,f.get('fvc_x_area')));
      return ee.Feature(null,{region:c.id,name:f.get('name'),year:y,scenes:z.n,scale_m:30,
        wetland_area_km2:total,valid_fvc_area_km2:valid,
        valid_fraction:ee.Algorithms.If(total.gt(0),valid.divide(total),null),
        fvc_mean_area_weighted:ee.Algorithms.If(valid.gt(0),weighted.divide(valid),null),
        soil_endpoint:c.soil,veg_endpoint:c.veg,status:ee.Algorithms.If(z.n.gt(0),'OBSERVED','NO_SCENES')});
    });
    cityRows.push(fc);
  });
});
var cityOut=ee.FeatureCollection(cityRows).flatten();
print('City QA expected records: 520 (41+11+13 cities x 8 years)',cityOut.size());
Export.table.toDrive({collection:cityOut,description:'Stage5_QA_City_FVC_8Nodes_30m',folder:EXPORT_FOLDER,fileNamePrefix:'Stage5_QA_City_FVC_8Nodes_30m',fileFormat:'CSV'});

// 2. Same image and mask, four reduceRegion scales.
var scaleRows=[];
CFG.forEach(function(c){
  SCALE_YEARS.forEach(function(y){
    var z=annualImages(c,y), target=z.fvc.updateMask(z.wet), area=ee.Image.pixelArea().divide(1e6);
    SCALES.forEach(function(s){
      var d=ee.Image.cat([area.updateMask(z.wet).rename('total'),area.updateMask(target.mask()).rename('valid'),target.multiply(area).rename('weighted')]).reduceRegion({reducer:ee.Reducer.sum(),geometry:z.roi,scale:s,maxPixels:1e13,tileScale:8});
      var total=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(d.get('total'),null),0,d.get('total')));
      var valid=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(d.get('valid'),null),0,d.get('valid')));
      var weighted=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(d.get('weighted'),null),0,d.get('weighted')));
      scaleRows.push(ee.Feature(null,{region:c.id,year:y,scale_m:s,scenes:z.n,wetland_area_km2:total,valid_area_km2:valid,
        valid_fraction:ee.Algorithms.If(total.gt(0),valid.divide(total),null),
        fvc_mean_area_weighted:ee.Algorithms.If(valid.gt(0),weighted.divide(valid),null)}));
    });
  });
});
Export.table.toDrive({collection:ee.FeatureCollection(scaleRows),description:'Stage5_QA_Scale_30_100_250_500m',folder:EXPORT_FOLDER,fileNamePrefix:'Stage5_QA_Scale_30_100_250_500m',fileFormat:'CSV'});

// 3. Observed-wetland NDVI percentile diagnostics. These are sensitivity
// diagnostics, not independently validated physical endpoints.
var epRows=[];
CFG.forEach(function(c){
  NODE_YEARS.forEach(function(y){
    var z=annualImages(c,y), wetNdvi=z.ndvi.updateMask(z.wet);
    var p=wetNdvi.reduceRegion({reducer:ee.Reducer.percentile([2,5,95,98]),geometry:z.roi,scale:30,maxPixels:1e13,tileScale:8});
    epRows.push(ee.Feature(null,{region:c.id,year:y,scenes:z.n,p02:p.get('NDVI_p2'),p05:p.get('NDVI_p5'),p95:p.get('NDVI_p95'),p98:p.get('NDVI_p98'),fixed_soil:c.soil,fixed_veg:c.veg,
      endpoint_status:'DISTRIBUTION_DIAGNOSTIC_NOT_EXTERNAL_VALIDATION'}));
  });
});
Export.table.toDrive({collection:ee.FeatureCollection(epRows),description:'Stage5_QA_Endpoint_Percentiles',folder:EXPORT_FOLDER,fileNamePrefix:'Stage5_QA_Endpoint_Percentiles',fileFormat:'CSV'});

// 4. Final 36-year regional series at 30 m. Split by region so the three
// exports can run in parallel and one slow region does not block the others.
CFG.forEach(function(c){
  var regionalRows=[];
  for(var y=1985;y<=2020;y++){
    var z=annualImages(c,y), target=z.fvc.updateMask(z.wet), area=ee.Image.pixelArea().divide(1e6);
    var d=ee.Image.cat([
      area.updateMask(z.wet).rename('wetland_area_km2'),
      area.updateMask(target.mask()).rename('valid_area_km2'),
      target.multiply(area).rename('fvc_x_area'),
      z.ndvi.updateMask(z.wet).multiply(area).rename('ndvi_x_area')
    ]).reduceRegion({reducer:ee.Reducer.sum(),geometry:z.roi,scale:30,maxPixels:1e13,tileScale:8});
    var total=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(d.get('wetland_area_km2'),null),0,d.get('wetland_area_km2')));
    var valid=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(d.get('valid_area_km2'),null),0,d.get('valid_area_km2')));
    var fw=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(d.get('fvc_x_area'),null),0,d.get('fvc_x_area')));
    var nw=ee.Number(ee.Algorithms.If(ee.Algorithms.IsEqual(d.get('ndvi_x_area'),null),0,d.get('ndvi_x_area')));
    regionalRows.push(ee.Feature(null,{region:c.id,year:y,scenes:z.n,scale_m:30,
      wetland_area_km2:total,valid_fvc_area_km2:valid,
      valid_fraction:ee.Algorithms.If(total.gt(0),valid.divide(total),null),
      fvc_mean_area_weighted:ee.Algorithms.If(valid.gt(0),fw.divide(valid),null),
      ndvi_mean_area_weighted:ee.Algorithms.If(valid.gt(0),nw.divide(valid),null),
      soil_endpoint:c.soil,veg_endpoint:c.veg,
      status:ee.Algorithms.If(z.n.gt(0),'OBSERVED','NO_SCENES')}));
  }
  Export.table.toDrive({collection:ee.FeatureCollection(regionalRows),
    description:'Stage5_Final_Regional30m_36Years_'+c.id,folder:EXPORT_FOLDER,
    fileNamePrefix:'Stage5_Final_Regional30m_36Years_'+c.id,fileFormat:'CSV'});
});

print('Existing QA tasks plus three split 36-year regional tasks are listed.');
print('Start only Stage5_Final_Regional30m_36Years_YRD/GBA/BTH on the second run.');
