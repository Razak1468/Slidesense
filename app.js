const NER_BOUNDS = [[21.5, 88.0], [29.7, 97.5]];
const NER_CENTER = [25.7, 92.8];
const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/SMAP_L4_Analyzed_Surface_Soil_Moisture/default/{time}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png";

const map = L.map("map",{center:NER_CENTER,zoom:5,minZoom:4,maxZoom:9});
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap contributors"}).addTo(map);
L.rectangle(NER_BOUNDS,{color:"#087f8c",weight:1.5,fill:false,interactive:false}).addTo(map);

let layer=null, opacity=.85;
const $=id=>document.getElementById(id);
function daysAgo(n){const d=new Date();d.setUTCDate(d.getUTCDate()-n);return d.toISOString().slice(0,10)}
function status(text,good=true,date="—"){$("status").textContent=text;$("statusDate").textContent=date;$("statusDot").style.background=good?"#21a36d":"#d65c4a"}

function loadLayer(date){
  if(layer) map.removeLayer(layer);
  layer=L.tileLayer(GIBS.replace("{time}",date),{
    opacity,maxNativeZoom:9,maxZoom:9,noWrap:true,attribution:"NASA SMAP / GIBS"
  });
  layer.on("load",()=>status("Satellite layer loaded",true,`Observation date: ${date}`));
  layer.on("tileerror",()=>status("No usable tiles for this date",false,"Try another date."));
  layer.addTo(map);
  status("Requesting satellite tiles…",true,`Observation date: ${date}`);
}

$("date").value=daysAgo(1); loadLayer($("date").value);
$("date").addEventListener("change",()=>loadLayer($("date").value));
$("latest").addEventListener("click",()=>{$("date").value=daysAgo(1);loadLayer($("date").value)});
$("fit").addEventListener("click",()=>map.fitBounds(NER_BOUNDS,{padding:[20,20]}));
$("opacity").addEventListener("click",()=>{opacity=opacity===.85?.6:opacity===.6?1:.85;if(layer)layer.setOpacity(opacity);$("opacity").textContent=`Opacity ${Math.round(opacity*100)}%`});
map.fitBounds(NER_BOUNDS,{padding:[20,20]});
