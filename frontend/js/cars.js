/**
 * 汽车销售顾问 — 车型库 / 知识库管理页
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
  const content = initLayout('车型库 / 知识库管理', 'cars');
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
        <h1>车型库 / 知识库管理</h1>
        <p>结构化车型用于工具调用，知识文档用于 RAG 检索增强。</p>
      </div>
      <div class="page-heading-meta">
        <span class="tag tag-blue">${carsData.length} 款车型</span>
        <span class="tag tag-success">${knowledgeDocs.length} 篇知识</span>
      </div>
    </div>

    <div class="kb-tabs" role="tablist">
      <button class="kb-tab ${activeTab === 'cars' ? 'active' : ''}" onclick="switchCarsTab('cars')">车型数据</button>
      <button class="kb-tab ${activeTab === 'knowledge' ? 'active' : ''}" onclick="switchCarsTab('knowledge')">知识文档</button>
      <button class="kb-tab ${activeTab === 'search' ? 'active' : ''}" onclick="switchCarsTab('search')">检索测试</button>
    </div>

    <section id="cars-tab-cars" class="kb-tab-panel ${activeTab === 'cars' ? 'active' : ''}">
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
    <div class="card">
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
              <th>油耗 / 续航</th>
              <th>主要卖点</th>
            </tr>
          </thead>
          <tbody id="cars-tbody"></tbody>
        </table>
      </div>
    </div>
  `;
}

function renderKnowledgeTab() {
  return `
    <div class="grid-2 kb-management-grid">
      <div class="card">
        <div class="card-header">
          <h3>新增知识文档</h3>
          <span class="tag tag-blue">自动切块</span>
        </div>
        <form class="kb-form" onsubmit="submitKnowledge(event)">
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

          <label class="form-label">知识内容</label>
          <textarea class="form-control kb-textarea" id="kb-content" placeholder="粘贴车型配置、优惠政策、竞品资料或销售话术..." required></textarea>

          <button class="btn btn-primary" id="kb-submit" type="submit">保存到知识库</button>
          <div class="hint" id="kb-save-status"></div>
        </form>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>RAG 流程说明</h3>
          <span class="tag tag-success">面试可讲</span>
        </div>
        <div class="rag-flow">
          <div><strong>1. 文档录入</strong><span>销售主管维护车型配置、优惠政策、竞品资料。</span></div>
          <div><strong>2. 文本切块</strong><span>后端按段落和句子拆成知识块，控制单块长度。</span></div>
          <div><strong>3. 知识入库</strong><span>保存到 knowledge_documents 和 knowledge_chunks。</span></div>
          <div><strong>4. 语义检索</strong><span>用户咨询时按问题召回相关知识片段。</span></div>
          <div><strong>5. 辅助回复</strong><span>检索结果作为上下文，和工具结果一起生成销售回复。</span></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>知识文档列表</h3>
        <span class="text-muted text-sm">${knowledgeDocs.length} 篇文档</span>
      </div>
      <div id="knowledge-list"></div>
    </div>
  `;
}

function renderSearchTab() {
  return `
    <div class="card">
      <div class="card-header">
        <h3>RAG 检索测试</h3>
        <span class="tag tag-blue">检索预览</span>
      </div>
      <div class="kb-search-row">
        <input class="form-control" id="kb-query" placeholder="例如：20万以内混动SUV怎么推荐？">
        <button class="btn btn-primary" onclick="testKnowledgeSearch()">检索</button>
      </div>
      <div class="hint">用于面试演示：输入用户问题，查看知识库召回了哪些片段。</div>
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
}

function renderKnowledgeList() {
  const el = document.getElementById('knowledge-list');
  if (!el) return;

  if (!knowledgeDocs.length) {
    el.innerHTML = '<div class="empty-state compact"><p>暂无知识文档</p><div class="hint">可以先新增一段优惠政策或销售话术。</div></div>';
    return;
  }

  el.innerHTML = knowledgeDocs.map(doc => `
    <article class="knowledge-item">
      <div class="knowledge-item-main">
        <div class="knowledge-title">${escapeHtml(doc.title)}</div>
        <div class="knowledge-preview">${escapeHtml(doc.content || '')}</div>
      </div>
      <div class="knowledge-meta">
        <span class="tag tag-blue">${DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}</span>
        <span class="tag tag-cold">${doc.chunks_count || 0} 个切片</span>
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
    status.textContent = `保存成功，生成 ${result.chunks} 个知识切片。`;
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

  resultEl.innerHTML = '<div class="card"><div class="loading compact"><div class="spinner"></div><p>正在检索知识库...</p></div></div>';
  try {
    const result = await api.searchKnowledge(query, 5);
    const docs = result.docs || [];
    resultEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <h3>检索结果</h3>
          <span class="text-muted text-sm">命中 ${docs.length} 个知识块</span>
        </div>
        ${docs.length ? docs.map(doc => `
          <article class="knowledge-result">
            <div class="knowledge-title">${escapeHtml(doc.title || '知识片段')}</div>
            <p>${escapeHtml(doc.content)}</p>
            <div class="knowledge-meta">
              <span class="tag tag-blue">${DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}</span>
              <span class="tag tag-cold">score ${(doc.score || 0).toFixed(3)}</span>
            </div>
          </article>
        `).join('') : '<div class="empty-state compact"><p>暂无命中结果</p><div class="hint">可以先新增相关知识文档。</div></div>'}
      </div>
    `;
  } catch (error) {
    console.error(error);
    resultEl.innerHTML = '<div class="card"><div class="empty-state compact"><p>检索失败</p><div class="hint">请检查知识库接口。</div></div></div>';
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
