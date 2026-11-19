document.addEventListener("DOMContentLoaded", () => {
  const menuToggle = document.getElementById("menuToggle");
  const navLinks = document.getElementById("navLinks");
  menuToggle?.addEventListener("click", () => navLinks.classList.toggle("open"));
  navLinks?.querySelectorAll("a").forEach(a => a.addEventListener("click", () => navLinks.classList.remove("open")));

  const cursorGlow = document.querySelector(".cursor-glow");
  if (cursorGlow && window.matchMedia("(pointer:fine)").matches) {
    window.addEventListener("mousemove", e => {
      cursorGlow.style.left = e.clientX + "px";
      cursorGlow.style.top = e.clientY + "px";
    });
  }

  const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        revealObserver.unobserve(entry.target);
      }
    });
  }, {threshold: 0.12});
  document.querySelectorAll(".reveal").forEach(el => revealObserver.observe(el));

  const cardsNode = document.getElementById("shopCards");
  if (!cardsNode) return;

  let shops = [];
  let userPosition = [11.3410, 77.7172];
  let map;
  let markerLayer;
  const mapNode = document.getElementById("map");
  if (mapNode && window.L) {
    map = L.map("map", {scrollWheelZoom:false}).setView(userPosition, 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    markerLayer = L.layerGroup().addTo(map);
    setTimeout(() => map.invalidateSize(), 350);
  }

  const distanceKm = (a,b) => {
    const rad = x => x * Math.PI / 180;
    const dLat = rad(b[0]-a[0]), dLon = rad(b[1]-a[1]);
    const x = Math.sin(dLat/2)**2 + Math.cos(rad(a[0]))*Math.cos(rad(b[0]))*Math.sin(dLon/2)**2;
    return 6371 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1-x));
  };
  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function renderShops() {
    const availability = document.getElementById("availabilityFilter").value;
    const sort = document.getElementById("sortFilter").value;
    let filtered = shops.map(s => ({...s, distance:distanceKm(userPosition,[Number(s.latitude),Number(s.longitude)])}));
    if (availability === "yes") filtered = filtered.filter(s => Number(s.available) === 1);
    filtered.sort((a,b) => sort === "price" ? Number(a.price)-Number(b.price) : sort === "distance" ? a.distance-b.distance : Number(b.rating)-Number(a.rating));
    document.getElementById("shopCount").textContent = `${filtered.length} repair shop${filtered.length===1?"":"s"} found`;
    cardsNode.innerHTML = filtered.length ? filtered.map((s,i) => `
      <article class="shop-card ${Number(s.available)!==1?'unavailable':''}" style="animation-delay:${i*70}ms">
        <div class="shop-symbol">⌁</div>
        <div class="shop-info"><h3>${escapeHtml(s.name)}</h3><p>${escapeHtml(s.address)}</p>
          <div class="shop-meta"><span class="rating">★ ${Number(s.rating).toFixed(1)}</span><span>⌖ ${s.distance.toFixed(1)} km</span><span>${Number(s.available)===1?'● Available':'○ Unavailable'}</span></div>
        </div>
        <div class="shop-price"><strong>₹${Number(s.price)}</strong><small>approx.</small>
          <button ${Number(s.available)!==1?'disabled':''} onclick="openBooking(${Number(s.id)})">Book service ↗</button>
        </div>
      </article>`).join("") : `<div class="empty-state"><h3>No shops match these filters</h3><p>Try changing the availability filter.</p></div>`;
    if (markerLayer) {
      markerLayer.clearLayers();
      filtered.forEach(s => {
        const marker = L.marker([s.latitude,s.longitude]).addTo(markerLayer);
        marker.bindPopup(`<b>${escapeHtml(s.name)}</b><br>₹${Number(s.price)} · ${s.distance.toFixed(1)} km<br>${Number(s.available)===1?'Available':'Unavailable'}`);
      });
      L.circle(userPosition,{radius:250,color:"#a8ff65",fillColor:"#a8ff65",fillOpacity:.08,weight:1}).addTo(markerLayer);
    }
  }

  fetch("/api/shops").then(r=>r.json()).then(data=>{shops=data;renderShops()}).catch(()=>{
    cardsNode.innerHTML='<div class="empty-state">Could not load repair shops. Please refresh.</div>';
  });
  document.getElementById("availabilityFilter").addEventListener("change",renderShops);
  document.getElementById("sortFilter").addEventListener("change",renderShops);

  document.getElementById("locateBtn").addEventListener("click", () => {
    const btn = document.getElementById("locateBtn");
    if (!navigator.geolocation) { alert("Location is not supported by this browser."); return; }
    btn.textContent = "Locating…";
    navigator.geolocation.getCurrentPosition(pos => {
      userPosition = [pos.coords.latitude,pos.coords.longitude];
      document.getElementById("locationText").value = `${userPosition[0].toFixed(4)}, ${userPosition[1].toFixed(4)}`;
      if (map) map.setView(userPosition,14);
      btn.innerHTML = "Location found ✓";
      renderShops();
    }, () => {
      btn.innerHTML = "Use my location ⌖";
      alert("Location permission was not granted. Showing sample Erode locations.");
    }, {enableHighAccuracy:true,timeout:10000});
  });
  window.openBooking = id => {
    const shop = shops.find(s=>Number(s.id)===Number(id));
    if (!shop) return;
    if (!window.PUNCTURE_CONFIG?.loggedIn) {
      window.location.href = "/login?next=/#find";
      return;
    }
    const name = prompt("Your full name:", window.PUNCTURE_CONFIG.userName || "");
    if (name === null) return;
    const phone = prompt("Your mobile number:");
    if (!phone) return;
    const vehicle = prompt("Vehicle type (Bike / Scooter):","Bike") || "Bike";
    const issue = prompt("Describe the issue (optional):","Rear tyre puncture") || "";
    const form = document.createElement("form");
    form.method="POST"; form.action=`/book/${id}`;
    const fields = {customer_name:name,phone,vehicle_type:vehicle,issue,latitude:userPosition[0],longitude:userPosition[1]};
    Object.entries(fields).forEach(([key,value])=>{
      const input=document.createElement("input");input.type="hidden";input.name=key;input.value=value;form.appendChild(input);
    });
    document.body.appendChild(form);form.submit();
  };
});
