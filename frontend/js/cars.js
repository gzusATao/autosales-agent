/**
 * 汽车销售顾问 — 车型库 / 销售资料库页面
 */

let carsData = [];
let knowledgeDocs = [];
let activeTab = 'cars';

const DOC_TYPE_LABELS = {
  car_config: '车型配置',
  policy: '优惠政策',
  competitor: '竞品资料',
  sales_script: '销售话术',
  general: '通用资料',
};

async function loadCars() {
  const content = initLayout('车型库 / 销售资料库', 'cars');
  content.innerHTML = `<div class="loading"><div class="spinner"></div><p>加载中...</p></div>`;

  try {
    const [cars, knowledge] = await Promise.all([
      api.getCars(),
      api.listKnowledge().catch(() => ({ docs: [] })),
    ]);
    carsData = cars || [];
    knowledgeDocs = knowledge.docs || [];
    renderCarsWorkspace(content);
  } catch (e) {
    console.error(e);
    content.innerHTML = '<div class="empty-state"><p>加载失败</p><div class="hint">请检查后端服务是否已启动</div></div>';
  }
}

function renderCarsWorkspace(content) {
  content.innerHTML = `
    <div class="page-heading">
      <div>
        <h1>车型库 / 销售资料库</h1>
        <p>车型档案用于工具调用，销售资料用于对话检索增强。</p>
      </div>
      <div class="page-heading-meta">
        <span class="tag tag-blue">${carsData.length} 款车型</span>
        <span class="tag tag-success">${knowledgeDocs.length} 篇资料</span>
      </div>
    </div>

    <div class="kb-tabs" role="tablist">
      <button class="kb-tab ${activeTab === 'cars' ? 'active' : ''}" onclick="switchCarsTab('cars')">车型档案</button>
      <button class="kb-tab ${activeTab === 'knowledge' ? 'active' : ''}" onclick="switchCarsTab('knowledge')">销售资料</button>
      <button class="kb-tab ${activeTab === 'search' ? 'active' : ''}" onclick="switchCarsTab('search')">资料检索</button>
    </div>

    <section id="cars-tab-cars" class="kb-tab-panel cars-tab-panel ${activeTab === 'cars' ? 'active' : ''}">
      ${renderCarsTab()}
    </section>
    <section id="cars-tab-knowledge" class="kb-tab-panel ${activeTab === 'knowledge' ? 'active' : ''}">
      ${renderKnowledgeTab()}
    </section>
    <section id="cars-tab-search" class="kb-tab-panel ${activeTab === 'search' ? 'active' : ''}">
      ${renderSearchTab()}
    </section>
  `;

  renderTable();
  renderKnowledgeList();
}

function switchCarsTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.kb-tab').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.kb-tab-panel').forEach(panel => panel.classList.remove('active'));
  document.querySelector(`.kb-tab[onclick="switchCarsTab('${tab}')"]`)?.classList.add('active');
  document.getElementById(`cars-tab-${tab}`)?.classList.add('active');
}

function renderCarsTab() {
  return `
    <div class="card cars-filter-card">
      <div class="form-row" style="gap:12px;">
        <select class="form-control" id="filter-brand" style="width:140px;" onchange="renderTable()">
          <option value="">全部品牌</option>
          ${[...new Set(carsData.map(c => c.brand))].map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join('')}
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
        <span class="text-muted text-sm" id="result-count">${carsData.length} 款车型</span>
      </div>
    </div>

    <div class="card responsive-table-card cars-table-card">
      <div class="table-wrap cars-table-scroll">
        <table>
          <thead>
            <tr>
              <th>品牌</th>
              <th>车型</th>
              <th>指导价</th>
              <th>能源类型</th>
              <th>车型级别</th>
              <th>座位</th>
              <th>油耗 / 续航</th>
              <th>主要卖点</th>
            </tr>
          </thead>
          <tbody id="cars-tbody"></tbody>
        </table>
      </div>
      <div class="mobile-record-list" id="cars-mobile-list"></div>
    </div>
  `;
}

function renderKnowledgeTab() {
  return `
    <div class="knowledge-workspace">
      <aside class="knowledge-side">
      <div class="card knowledge-tool-card">
        <div class="card-header">
          <h3>上传销售资料</h3>
          <span class="tag tag-blue">Pandas 清洗</span>
        </div>
        <form class="kb-form compact" onsubmit="submitKnowledgeFile(event)">
          <label class="form-label">选择文件</label>
          <label class="kb-upload-box compact" for="kb-file">
            <input id="kb-file" type="file" accept=".pdf,.txt,.docx,.md" required>
            <strong>点击上传 PDF / TXT / Word / MD</strong>
            <span>系统会抽取文本，使用 Pandas 去空行、去重复段落，再切块入库。</span>
          </label>

          <label class="form-label">文档标题（可选）</label>
          <input class="form-control" id="kb-file-title" placeholder="不填则使用文件名">

          <label class="form-label">文档类型</label>
          <select class="form-control" id="kb-file-type">
            <option value="car_config">车型配置</option>
            <option value="policy">优惠政策</option>
            <option value="competitor">竞品资料</option>
            <option value="sales_script">销售话术</option>
            <option value="general">通用资料</option>
          </select>

          <button class="btn btn-primary" id="kb-file-submit" type="submit">上传并入库</button>
          <div class="hint" id="kb-file-status"></div>
        </form>
      </div>

      <div class="card knowledge-tool-card">
        <div class="card-header">
          <h3>手动录入资料</h3>
          <span class="tag tag-cold">文本切块</span>
        </div>
        <form class="kb-form compact" onsubmit="submitKnowledge(event)">
          <label class="form-label">文档标题</label>
          <input class="form-control" id="kb-title" placeholder="例如：Model Y 竞品对比话术" required>

          <label class="form-label">文档类型</label>
          <select class="form-control" id="kb-type">
            <option value="car_config">车型配置</option>
            <option value="policy">优惠政策</option>
            <option value="competitor">竞品资料</option>
            <option value="sales_script">销售话术</option>
            <option value="general">通用资料</option>
          </select>

          <label class="form-label">资料内容</label>
          <textarea class="form-control kb-textarea compact" id="kb-content" placeholder="粘贴车型配置、优惠政策、竞品资料或销售话术..." required></textarea>

          <button class="btn btn-primary" id="kb-submit" type="submit">保存到资料库</button>
          <div class="hint" id="kb-save-status"></div>
        </form>
      </div>

      </aside>

    <div class="card knowledge-list-card">
      <div class="card-header">
        <h3>销售资料列表</h3>
        <span class="text-muted text-sm">${knowledgeDocs.length} 篇文档</span>
      </div>
      <div id="knowledge-list"></div>
    </div>
    </div>
  `;
}

async function submitKnowledgeFile(event) {
  event.preventDefault();
  const fileInput = document.getElementById('kb-file');
  const submitBtn = document.getElementById('kb-file-submit');
  const status = document.getElementById('kb-file-status');
  const title = document.getElementById('kb-file-title').value.trim();
  const docType = document.getElementById('kb-file-type').value;
  const file = fileInput?.files?.[0];

  if (!file) {
    status.textContent = '请先选择一个销售资料文件。';
    return;
  }

  submitBtn.disabled = true;
  status.textContent = '正在抽取文本、清洗段落并切块入库...';

  try {
    const result = await api.uploadKnowledgeFile(file, docType, title);
    status.textContent = `上传成功，生成 ${result.chunks} 个资料切片。`;
    fileInput.value = '';
    document.getElementById('kb-file-title').value = '';
    const list = await api.listKnowledge();
    knowledgeDocs = list.docs || [];
    renderKnowledgeList();
  } catch (error) {
    console.error(error);
    status.textContent = '上传失败，请确认文件格式为 PDF、TXT、DOCX 或 MD。';
  } finally {
    submitBtn.disabled = false;
  }
}

function renderSearchTab() {
  return `
    <div class="card">
      <div class="card-header">
        <h3>资料检索</h3>
        <span class="tag tag-blue">检索预览</span>
      </div>
      <div class="kb-search-row">
        <input class="form-control" id="kb-query" placeholder="例如：20万以内混动SUV怎么推荐？">
        <button class="btn btn-primary" onclick="testKnowledgeSearch()">检索</button>
      </div>
      <div class="hint">输入客户问题，查看销售资料库召回了哪些相关片段。</div>
    </div>

    <div id="kb-search-results"></div>
  `;
}

function renderTable() {
  const brand = document.getElementById('filter-brand')?.value || '';
  const type = document.getElementById('filter-type')?.value || '';
  const energy = document.getElementById('filter-energy')?.value || '';
  const price = document.getElementById('filter-price')?.value || '';

  let filtered = carsData;
  if (brand) filtered = filtered.filter(c => c.brand === brand);
  if (type) filtered = filtered.filter(c => c.car_type === type);
  if (energy) filtered = filtered.filter(c => c.energy_type === energy);
  if (price) {
    const [min, max] = price.split('-').map(Number);
    if (max) filtered = filtered.filter(c => c.price >= min * 10000 && c.price <= max * 10000);
    else filtered = filtered.filter(c => price === '10' ? c.price < 100000 : c.price > 300000);
  }

  const resultCount = document.getElementById('result-count');
  if (resultCount) resultCount.textContent = `${filtered.length} 款车型`;

  const tbody = document.getElementById('cars-tbody');
  const mobileList = document.getElementById('cars-mobile-list');
  if (!tbody) return;

  tbody.innerHTML = filtered.map(c => `
    <tr>
      <td><strong>${escapeHtml(c.brand)}</strong></td>
      <td>${escapeHtml(c.model)}</td>
      <td><strong>¥${(c.price / 10000).toFixed(1)}万</strong></td>
      <td><span class="tag ${energyTagClass(c.energy_type)}">${escapeHtml(c.energy_type)}</span></td>
      <td><span class="tag tag-blue">${escapeHtml(c.car_type)}</span></td>
      <td>${c.seat_count}座</td>
      <td>${escapeHtml(c.fuel_consumption || c.range_km || '-')}</td>
      <td style="max-width:220px;white-space:normal;">
        ${(c.highlights || []).slice(0, 3).map(h => `<span class="tag tag-cold" style="margin:1px;">${escapeHtml(h)}</span>`).join('')}
      </td>
    </tr>
  `).join('') || '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted);">无匹配车型</td></tr>';

  if (mobileList) {
    mobileList.innerHTML = filtered.map(c => `
      <article class="mobile-record-card">
        <div class="mobile-record-head">
          <div>
            <div class="mobile-record-title">${escapeHtml(c.brand)} ${escapeHtml(c.model)}</div>
            <div class="mobile-record-subtitle">¥${(c.price / 10000).toFixed(1)}万 · ${c.seat_count}座</div>
          </div>
          <span class="tag tag-blue">${escapeHtml(c.car_type)}</span>
        </div>
        <div class="mobile-record-meta">
          <div><span>能源</span><strong>${escapeHtml(c.energy_type)}</strong></div>
          <div><span>油耗/续航</span><strong>${escapeHtml(c.fuel_consumption || c.range_km || '-')}</strong></div>
        </div>
        <div class="mobile-record-tags">
          ${(c.highlights || []).slice(0, 4).map(h => `<span class="tag tag-cold">${escapeHtml(h)}</span>`).join('')}
        </div>
      </article>
    `).join('') || '<div class="mobile-empty-card">无匹配车型</div>';
  }
}

function renderKnowledgeList() {
  const el = document.getElementById('knowledge-list');
  if (!el) return;

  if (!knowledgeDocs.length) {
    el.innerHTML = '<div class="empty-state compact"><p>暂无销售资料</p><div class="hint">可以先新增一段优惠政策或销售话术。</div></div>';
    return;
  }

  el.className = 'knowledge-grid';
  el.innerHTML = knowledgeDocs.map(doc => `
    <article class="knowledge-item">
      <div class="knowledge-icon" aria-hidden="true">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>
          <path d="M14 3v5h5"/>
          <path d="M8.5 12h7"/>
          <path d="M8.5 15h5.5"/>
        </svg>
      </div>
      <div class="knowledge-item-main">
        <div class="knowledge-title">${escapeHtml(doc.title)}</div>
        <div class="knowledge-preview">${escapeHtml(doc.content || '')}</div>
        <div class="knowledge-meta">
          <span class="tag tag-blue">${DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}</span>
          <span class="tag tag-cold">${doc.chunks_count || 0} 个切片</span>
        </div>
      </div>
    </article>
  `).join('');
}

async function submitKnowledge(event) {
  event.preventDefault();
  const submitBtn = document.getElementById('kb-submit');
  const status = document.getElementById('kb-save-status');
  const title = document.getElementById('kb-title').value.trim();
  const docType = document.getElementById('kb-type').value;
  const content = document.getElementById('kb-content').value.trim();

  if (!title || !content) return;
  submitBtn.disabled = true;
  status.textContent = '正在切块并保存...';

  try {
    const result = await api.uploadKnowledge({
      title,
      doc_type: docType,
      content,
      metadata: { source: '车型库管理页' },
    });
    status.textContent = `保存成功，生成 ${result.chunks} 个资料切片。`;
    document.getElementById('kb-title').value = '';
    document.getElementById('kb-content').value = '';
    const list = await api.listKnowledge();
    knowledgeDocs = list.docs || [];
    renderKnowledgeList();
  } catch (error) {
    console.error(error);
    status.textContent = '保存失败，请检查后端服务。';
  } finally {
    submitBtn.disabled = false;
  }
}

async function testKnowledgeSearch() {
  const query = document.getElementById('kb-query')?.value.trim();
  const resultEl = document.getElementById('kb-search-results');
  if (!query || !resultEl) return;

  resultEl.innerHTML = '<div class="card"><div class="loading compact"><div class="spinner"></div><p>正在检索销售资料库...</p></div></div>';
  try {
    const result = await api.searchKnowledge(query, 5);
    const docs = result.docs || [];
    resultEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <h3>检索结果</h3>
          <span class="text-muted text-sm">命中 ${docs.length} 个资料片段</span>
        </div>
        ${docs.length ? docs.map(doc => `
          <article class="knowledge-result">
            <div class="knowledge-title">${escapeHtml(doc.title || '资料片段')}</div>
            <p>${escapeHtml(doc.content)}</p>
            <div class="knowledge-meta">
              <span class="tag tag-blue">${DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}</span>
              <span class="tag tag-cold">score ${(doc.score || 0).toFixed(3)}</span>
            </div>
          </article>
        `).join('') : '<div class="empty-state compact"><p>暂无命中结果</p><div class="hint">可以先新增相关销售资料。</div></div>'}
      </div>
    `;
  } catch (error) {
    console.error(error);
    resultEl.innerHTML = '<div class="card"><div class="empty-state compact"><p>检索失败</p><div class="hint">请检查销售资料接口。</div></div></div>';
  }
}

function energyTagClass(energyType) {
  if (energyType === '纯电') return 'tag-success';
  if (energyType === '混动' || energyType === '插电混动') return 'tag-warm';
  return 'tag-cold';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

loadCars();
