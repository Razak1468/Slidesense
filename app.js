const $ = id => document.getElementById(id);
const map = L.map('map').setView([27.3, 92.5], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
let marker;

map.on('click', e => {
  $('latitude').value = e.latlng.lat.toFixed(4);
  $('longitude').value = e.latlng.lng.toFixed(4);
  $('coords').textContent = `${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
  if(marker) marker.setLatLng(e.latlng); else marker = L.marker(e.latlng).addTo(map);
});

async function health(){
  const r = await fetch('/api/health'); const j = await r.json();
  $('status').textContent = j.model_loaded ? '● Model ready' : '○ Model not trained';
  $('status').style.color = j.model_loaded ? '#6ee7b7' : '#fbbf24';
}

async function metrics(){
  const r = await fetch('/api/metrics'); const j = await r.json();
  if(!j.trained){ $('modelInfo').textContent = 'No trained model found. Run the data pipeline and training script.'; return; }
  $('modelInfo').textContent = `Validation: ${j.validation}. ${j.note}`;
  $('metrics').innerHTML = `
    <div><span>Rows</span><b>${j.rows}</b></div>
    <div><span>ROC-AUC</span><b>${Number(j.roc_auc).toFixed(3)}</b></div>
    <div><span>PR-AUC</span><b>${Number(j.average_precision).toFixed(3)}</b></div>`;
}

function payload(){
  return Object.fromEntries(['latitude','longitude','elevation_m','rainfall_24h_mm','rainfall_3d_mm','rainfall_7d_mm','forecast_rainfall_24h_mm','soil_moisture_m3m3','slope_deg'].map(k => [k, Number($(k).value)]));
}

$('predict').onclick = async () => {
  const button = $('predict'); button.disabled = true; button.textContent = 'Running model…';
  try{
    const r = await fetch('/api/predict', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload())});
    const j = await r.json();
    if(!r.ok) throw new Error(j.detail || 'Prediction failed');
    const p = j.landslide_probability * 100;
    $('probability').textContent = `${p.toFixed(1)}%`;
    $('meterFill').style.width = `${p}%`;
    $('riskBadge').textContent = j.risk_level;
    $('riskBadge').className = `badge ${j.risk_level.toLowerCase().replace(' ','')}`;
    $('resultText').textContent = j.warning;
    if(marker) marker.setLatLng([j.latitude,j.longitude]); else marker=L.marker([j.latitude,j.longitude]).addTo(map);
    map.setView([j.latitude,j.longitude], Math.max(map.getZoom(),8));
  }catch(e){ $('resultText').textContent = e.message; }
  finally{ button.disabled=false; button.textContent='Run risk prediction'; }
};
health(); metrics();
