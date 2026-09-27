const API="http://localhost:8000";
let map, markers=[], chart;
const $=id=>document.getElementById(id);

function riskClass(p){return p<30?"low":p<55?"med":p<75?"high":"severe"}
function paintRisk(p){
  const cls=riskClass(p), deg=Math.round(p*3.6);
  const colors={low:"#61e6ad",med:"#f4bd61",high:"#ff8b67",severe:"#ff5d6c"};
  $("riskRing").style.background=`conic-gradient(${colors[cls]} ${deg}deg,#182c27 ${deg}deg)`;
  $("risk").textContent=p.toFixed(0)+"%";
  $("riskText").textContent=p<30?"Current conditions indicate a lower prototype risk signal.":p<55?"The model sees a moderate risk signal; monitor rainfall and soil conditions.":p<75?"Elevated risk signal. Increasing rainfall or wet soil can raise the estimate.":"Very high prototype signal. This must not be treated as an operational warning.";
}
function clearMarkers(){markers.forEach(m=>m.remove());markers=[]}
function markerColor(p){return p<30?"#61e6ad":p<55?"#f4bd61":p<75?"#ff8b67":"#ff5d6c"}
function drawGrid(points){
  clearMarkers();
  points.forEach(x=>{
    const m=L.circleMarker([x.lat,x.lon],{radius:10,weight:1,color:"#08110f",fillColor:markerColor(x.risk),fillOpacity:.65});
    m.bindTooltip(`Prototype risk: ${x.risk}%`);
    m.addTo(map);markers.push(m);
  });
}
function drawChart(rows){
  const ctx=$("chart").getContext("2d");
  if(chart) chart.destroy();
  chart=new Chart(ctx,{type:"line",data:{labels:rows.map(x=>new Date(x.time).toLocaleString([], {weekday:"short",hour:"2-digit"})),datasets:[{data:rows.map(x=>x.risk),tension:.35,borderWidth:2,pointRadius:2}]},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:"#78918a",maxTicksLimit:7},grid:{display:false}},y:{min:0,max:100,ticks:{color:"#78918a",callback:v=>v+"%"},grid:{color:"#1e312d"}}}}});
}
async function analyze(lat,lon){
  $("risk").textContent="…";
  try{
    const r=await fetch(`${API}/api/risk?lat=${lat}&lon=${lon}`).then(x=>x.json());
    const c=r.current;
    paintRisk(c.risk);
    $("temp").textContent=c.temperature+"°C";
    $("humidity").textContent=c.humidity+"%";
    $("rainSignal").textContent=(r.future[0]?.rain_24h??"—")+" mm/24h";
    $("events").textContent=r.nearby_event_count;
    $("updated").textContent=new Date().toLocaleTimeString();
    drawChart(r.future);
    $("futureNote").textContent=`The forecast path reaches a maximum prototype model risk of ${Math.max(...r.future.map(x=>x.risk)).toFixed(0)}%. Forecast rainfall is one of the model inputs.`;
    $("drivers").innerHTML=`
      <div class="driver"><b>Weather model probability: ${c.model_probability}%</b><span>Learned prototype signal from rainfall, humidity, soil moisture, pressure, wind and terrain proxy.</span></div>
      <div class="driver"><b>Historical catalog evidence: ${c.historical_evidence}%</b><span>${r.nearby_event_count} NASA GLC events found within the evidence radius.</span></div>
      <div class="driver"><b>Forecast-aware</b><span>Future rainfall is passed through the model instead of only displaying weather.</span></div>`;
    $("eventList").innerHTML=r.events.length?r.events.map(e=>`<div class="event"><span>${e.date}</span><b>${e.distance_km} km away</b></div>`).join(""):`<div class="note">No nearby catalog events were returned for this location.</div>`;
    map.setView([lat,lon],9);
    const grid=await fetch(`${API}/api/map-grid?lat=${lat}&lon=${lon}`).then(x=>x.json());
    drawGrid(grid.points);
    L.marker([lat,lon]).addTo(map).bindPopup("<b>Selected location</b><br>SlideSpect analysis").openPopup();
  }catch(e){console.error(e);$("riskText").textContent="Could not load the data. Check that the backend is running and that the network is available."}
}
async function searchPlace(){
  const q=$("place").value.trim(); if(!q)return;
  const d=await fetch(`${API}/api/geocode?name=${encodeURIComponent(q)}`).then(x=>x.json());
  if(d.results?.length){const x=d.results[0]; analyze(x.latitude,x.longitude)}
}
$("searchBtn").onclick=searchPlace;
$("place").addEventListener("keydown",e=>{if(e.key==="Enter")searchPlace()});
$("locBtn").onclick=()=>navigator.geolocation?.getCurrentPosition(p=>analyze(p.coords.latitude,p.coords.longitude),()=>alert("Location permission was not granted."));
map=L.map("map").setView([20.5937,78.9629],5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap contributors"}).addTo(map);
analyze(20.5937,78.9629);
