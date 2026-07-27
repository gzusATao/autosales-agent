/**
 * AutoLead Agent — API 客户端
 */

const API_BASE = '/api';

const api = {
    async request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (body) opts.body = JSON.stringify(body);

        const resp = await fetch(`${API_BASE}${path}`, opts);
        if (!resp.ok) {
            throw new Error(`API Error: ${resp.status} ${resp.statusText}`);
        }
        return resp.json();
    },

    async requestForm(method, path, formData) {
        const resp = await fetch(`${API_BASE}${path}`, {
            method,
            body: formData,
        });
        if (!resp.ok) {
            const detail = await resp.text();
            throw new Error(`API Error: ${resp.status} ${detail || resp.statusText}`);
        }
        return resp.json();
    },

    // 对话
    chat(message, sessionId = '', customerId = '') {
        return this.request('POST', '/chat/message', {
            session_id: sessionId,
            customer_id: customerId,
            message,
        });
    },

    // 客户
    getCustomerProfile(id) {
        return this.request('GET', `/customers/${id}/profile`);
    },
    getLeads() {
        return this.request('GET', '/leads');
    },

    // 车型
    getCars() {
        return this.request('GET', '/cars');
    },
    compareCars(models) {
        return this.request('POST', '/cars/compare', { models });
    },

    // 金融
    calculateLoan(carPrice, downRate = 0.3, years = 3, rate = 0.045) {
        return this.request('POST', '/finance/calculate', {
            car_price: carPrice,
            down_payment_rate: downRate,
            years,
            annual_rate: rate,
        });
    },

    // 库存
    queryInventory(model = '', city = '', color = '') {
        const params = new URLSearchParams({ model, city, color });
        return this.request('GET', `/inventory?${params}`);
    },

    // 试驾
    createAppointment(data) {
        return this.request('POST', '/appointments', data);
    },
    getAppointments() {
        return this.request('GET', '/appointments');
    },

    // 知识库
    listKnowledge() {
        return this.request('GET', '/knowledge');
    },
    uploadKnowledge(data) {
        return this.request('POST', '/knowledge/upload', data);
    },
    uploadKnowledgeFile(file, docType = 'general', title = '') {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('doc_type', docType);
        if (title) formData.append('title', title);
        return this.requestForm('POST', '/knowledge/upload-file', formData);
    },
    searchKnowledge(query, topK = 5) {
        return this.request('POST', '/knowledge/search', { query, top_k: topK });
    },

    health() {
        return this.request('GET', '/health');
    },
};

async function initModelBadge() {
    try {
        const health = await api.health();
        const provider = (health.llm_provider || 'mock').toLowerCase();
        window.__MODEL_MODE = provider;

        const badge = document.getElementById('model-badge');
        if (!badge) return;

        const isDeepSeek = provider === 'deepseek';
        badge.className = `topbar-badge ${isDeepSeek ? 'deepseek' : 'mock'}`;
        badge.textContent = isDeepSeek ? 'DeepSeek' : 'Mock LLM';
    } catch (error) {
        console.warn('Failed to load model mode', error);
    }
}

document.addEventListener('DOMContentLoaded', initModelBadge);
