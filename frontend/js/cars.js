/**
 * AutoSales Agent — 车型库页（数据管理）
 */

async function loadCars() {
  const content = initLayout('车型库', 'cars');
  content.innerHTML = `<div class="loading"><div class="spinner"></div><p>加载中...</p></div>`;

  try {
    const cars = await api.getCars();

    content.innerHTML = `
      <!-- 筛选区 -->
      <div class="card">
        <div class="form-row" style="gap:12px;">
          <select class="form-control" id="filter-brand" style="width:140px;" onchange="renderTable()">
            <option value="">全部品牌</option>
            ${[...new Set(cars.map(c => c.brand))].map(b => `<option value="${b}">${b}</option>`).join('')}
          </select>
          <select class="form-control" id="filter-type" style="width:120px;" onchange="renderTable()">
            <option value="">全部级别</option>
            <option value="SUV">SUV</option>
            <option value="轿车">轿车</option>
          </select>
          <select class="form-control" id="filter-energy" style="width:130px;" onchange="renderTable()">
            <option value="">全部能源</option>
            <option value="燃油">燃油</option>
            <option value="混动">混动</option>
            <option value="插电混动">插电混动</option>
            <option value="纯电">纯电</option>
          </select>
          <select class="form-control" id="filter-price" style="width:140px;" onchange="renderTable()">
            <option value="">全部价格</option>
            <option value="10">10万以下</option>
            <option value="10-20">10-20万</option>
            <option value="20-30">20-30万</option>
            <option value="30">30万以上</option>
          </select>
          <span class="text-muted text-sm" id="result-count">${cars.length} 款车型</span>
        </div>
      </div>

      <!-- 表格 -->
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>品牌</th>
                <th>车型</th>
                <th>指导价</th>
                <th>能源类型</th>
                <th>车型级别</th>
                <th>座位</th>
                <th>油耗/续航</th>
                <th>主要卖点</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody id="cars-tbody"></tbody>
          </table>
        </div>
      </div>
    `;

    window.__carsData = cars;
    renderTable();
  } catch (e) {
    console.error(e);
    content.innerHTML = '<div class="empty-state"><p>加载失败</p><div class="hint">请检查后端服务</div></div>';
  }
}

function renderTable() {
  const cars = window.__carsData || [];
  const brand = document.getElementById('filter-brand')?.value || '';
  const type = document.getElementById('filter-type')?.value || '';
  const energy = document.getElementById('filter-energy')?.value || '';
  const price = document.getElementById('filter-price')?.value || '';

  let filtered = cars;
  if (brand) filtered = filtered.filter(c => c.brand === brand);
  if (type) filtered = filtered.filter(c => c.car_type === type);
  if (energy) filtered = filtered.filter(c => c.energy_type === energy);
  if (price) {
    const [min, max] = price.split('-').map(Number);
    if (max) filtered = filtered.filter(c => c.price >= min * 10000 && c.price <= max * 10000);
    else filtered = filtered.filter(c => price === '10' ? c.price < 100000 : c.price > 300000);
  }

  document.getElementById('result-count').textContent = `${filtered.length} 款车型`;

  const tbody = document.getElementById('cars-tbody');
  if (!tbody) return;

  tbody.innerHTML = filtered.map(c => `
    <tr>
      <td><strong>${c.brand}</strong></td>
      <td>${c.model}</td>
      <td><strong>¥${(c.price / 10000).toFixed(1)}万</strong></td>
      <td><span class="tag ${c.energy_type === '纯电' ? 'tag-success' : c.energy_type === '混动' || c.energy_type === '插电混动' ? 'tag-warm' : 'tag-cold'}">${c.energy_type}</span></td>
      <td><span class="tag tag-blue">${c.car_type}</span></td>
      <td>${c.seat_count}座</td>
      <td>${c.fuel_consumption || c.range_km || '-'}</td>
      <td style="max-width:200px;white-space:normal;">
        ${(c.highlights || []).slice(0, 3).map(h => `<span class="tag tag-cold" style="margin:1px;">${h}</span>`).join('')}
      </td>
      <td>
        <div class="btn-group">
          <button class="btn btn-sm btn-ghost" onclick="api.compareCars(['${c.model}','']).catch(()=>{})">对比</button>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-muted);">无匹配车型</td></tr>';
}

loadCars();
