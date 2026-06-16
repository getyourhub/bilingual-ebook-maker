(() => {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const STORAGE_KEY = "ebook-maker-settings";

    const state = {
        taskId: null,
        filepath: null,
        filename: null,
        provider: "google",
        ws: null
    };

    const PROVIDER_MODELS = {
        google: [],
        gemini: [
            {id: "gemini-2.5-flash", name: "Gemini 2.5 Flash"},
            {id: "gemini-2.5-pro", name: "Gemini 2.5 Pro"},
            {id: "gemini-2.0-flash", name: "Gemini 2.0 Flash"}
        ],
        claude: [
            {id: "claude-3-5-sonnet-20241022", name: "Claude 3.5 Sonnet"},
            {id: "claude-3-5-haiku-20241022", name: "Claude 3.5 Haiku"}
        ],
        deepseek: [
            {id: "deepseek-chat", name: "DeepSeek V3"},
            {id: "deepseek-reasoner", name: "DeepSeek R1"}
        ],
        qwen: [
            {id: "qwen-turbo", name: "Qwen Turbo"},
            {id: "qwen-plus", name: "Qwen Plus"},
            {id: "qwen-max", name: "Qwen Max"},
            {id: "qwen3-235b-a22b", name: "Qwen3 235B"}
        ],
        mimo: [
            {id: "mimo-v2.5-pro", name: "MiMo V2.5 Pro"}
        ],
        mimo_tokenplan: [
            {id: "mimo-v2.5-pro", name: "MiMo V2.5 Pro"},
            {id: "mimo-v2-flash", name: "MiMo V2 Flash"}
        ],
        deepl: [],
        openrouter: [
            {id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet"},
            {id: "anthropic/claude-3.5-haiku", name: "Claude 3.5 Haiku"},
            {id: "google/gemini-2.5-flash", name: "Gemini 2.5 Flash"},
            {id: "deepseek/deepseek-chat-v3", name: "DeepSeek V3"},
            {id: "deepseek/deepseek-r1", name: "DeepSeek R1"},
            {id: "qwen/qwen3-235b-a22b", name: "Qwen3 235B"}
        ],
        siliconflow: [
            {id: "deepseek-ai/DeepSeek-V3", name: "DeepSeek V3"},
            {id: "deepseek-ai/DeepSeek-R1", name: "DeepSeek R1"},
            {id: "Qwen/Qwen3-235B-A22B", name: "Qwen3 235B"},
            {id: "Pro/deepseek-ai/DeepSeek-V3", name: "DeepSeek V3 (Pro)"}
        ],
        custom: []
    };

    const PROVIDER_NEEDS_KEY = {
        google: false, deepl: true, gemini: true, claude: true,
        deepseek: true, qwen: true, mimo: true, mimo_tokenplan: true,
        openrouter: true, siliconflow: true, custom: true
    };

    // Load saved settings
    function loadSettings() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            return saved ? JSON.parse(saved) : {};
        } catch { return {}; }
    }

    function saveSettings(settings) {
        try {
            const current = loadSettings();
            localStorage.setItem(STORAGE_KEY, JSON.stringify({...current, ...settings}));
        } catch (e) { console.error("Failed to save settings:", e); }
    }

    function getProviderSettings(provider) {
        const settings = loadSettings();
        return settings[`provider_${provider}`] || {};
    }

    function saveProviderSettings(provider, data) {
        const settings = loadSettings();
        settings[`provider_${provider}`] = data;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    }

    // Elements
    const dropZone = $('#drop-zone');
    const fileInput = $('#file-input');
    const browseBtn = $('#browse-btn');
    const fileInfo = $('#file-info');
    const fileName = $('#file-name');
    const fileMeta = $('#file-meta');
    const removeFile = $('#remove-file');
    const uploadSection = $('#upload-section');
    const providerSection = $('#provider-section');
    const progressSection = $('#progress-section');
    const resultSection = $('#result-section');
    const startBtn = $('#start-btn');
    const downloadBtn = $('#download-btn');
    const restartBtn = $('#restart-btn');

    // Load saved defaults
    const savedSettings = loadSettings();
    if (savedSettings.defaultProvider) {
        state.provider = savedSettings.defaultProvider;
    }

    // File upload
    ['dragenter', 'dragover'].forEach(e => {
        dropZone.addEventListener(e, (ev) => { ev.preventDefault(); dropZone.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(e => {
        dropZone.addEventListener(e, (ev) => { ev.preventDefault(); dropZone.classList.remove('dragover'); });
    });
    dropZone.addEventListener('drop', (e) => { if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]); });
    dropZone.addEventListener('click', () => fileInput.click());
    browseBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
    fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });
    removeFile.addEventListener('click', resetAll);

    async function handleFile(file) {
        if (!file.name.match(/\.(epub|pdf)$/i)) {
            alert('Please select a .epub or .pdf file\n请选择 .epub 或 .pdf 文件');
            return;
        }
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.error) { alert(data.error); return; }

            state.taskId = data.task_id;
            state.filepath = data.filepath;
            state.filename = data.filename;

            fileName.textContent = data.filename;
            fileMeta.textContent = `${data.book_info.type} · ${data.book_info.author}`;
            fileInfo.classList.remove('hidden');
            dropZone.classList.add('hidden');

            $('#preview-title-mini').textContent = `${data.book_info.title} — ${data.book_info.author}`;
            providerSection.classList.remove('hidden');
            providerSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } catch (err) {
            alert('Upload failed: ' + err.message);
        }
    }

    // Provider selection
    $$('.provider-card').forEach(card => {
        card.addEventListener('click', () => {
            $$('.provider-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            state.provider = card.dataset.provider;
            updateProviderUI();
            loadSavedProviderSettings();
        });
    });

    function updateProviderUI() {
        const p = state.provider;
        const needsKey = PROVIDER_NEEDS_KEY[p];
        const models = PROVIDER_MODELS[p] || [];
        const isCustom = p === 'custom';

        const modelRow = $('#model-row');
        const modelSelect = $('#model-select');
        const keyRow = $('#api-key-row');
        const customUrlRow = $('#custom-url-row');
        const customModelRow = $('#custom-model-row');

        if (models.length > 0) {
            modelRow.classList.remove('hidden');
            modelSelect.innerHTML = models.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
        } else if (isCustom) {
            modelRow.classList.add('hidden');
        } else {
            modelRow.classList.add('hidden');
        }

        if (needsKey) {
            keyRow.classList.remove('hidden');
        } else {
            keyRow.classList.add('hidden');
        }

        if (isCustom) {
            customUrlRow.classList.remove('hidden');
            customModelRow.classList.remove('hidden');
            keyRow.classList.remove('hidden');
        } else {
            customUrlRow.classList.add('hidden');
            customModelRow.classList.add('hidden');
        }
    }

    function loadSavedProviderSettings() {
        const p = state.provider;
        const saved = getProviderSettings(p);

        if (saved.apiKey) $('#api-key').value = saved.apiKey;
        if (saved.model) $('#model-select').value = saved.model;
        if (saved.customUrl) $('#custom-url').value = saved.customUrl;
        if (saved.customModel) $('#custom-model').value = saved.customModel;
    }

    // Save provider settings
    $('#save-provider-btn').addEventListener('click', () => {
        const p = state.provider;
        const data = {
            apiKey: $('#api-key').value,
            model: $('#model-select').value,
            customUrl: $('#custom-url').value,
            customModel: $('#custom-model').value
        };
        saveProviderSettings(p, data);

        const feedback = $('#save-feedback');
        feedback.classList.remove('hidden');
        setTimeout(() => feedback.classList.add('hidden'), 2000);
    });

    // Toggle key visibility
    $('#toggle-key').addEventListener('click', () => {
        const input = $('#api-key');
        input.type = input.type === 'password' ? 'text' : 'password';
    });

    // Save defaults
    $('#save-defaults-btn').addEventListener('click', () => {
        const defaultProvider = $('#default-provider').value;
        const fallbackProvider = $('#fallback-provider').value;
        saveSettings({ defaultProvider, fallbackProvider });

        const feedback = $('#defaults-feedback');
        feedback.classList.remove('hidden');
        setTimeout(() => feedback.classList.add('hidden'), 2000);
    });

    // Load saved defaults on init
    function loadDefaults() {
        const settings = loadSettings();
        if (settings.defaultProvider) {
            $('#default-provider').value = settings.defaultProvider;
            state.provider = settings.defaultProvider;
            // Update active card
            $$('.provider-card').forEach(c => {
                c.classList.toggle('active', c.dataset.provider === settings.defaultProvider);
            });
        }
        if (settings.fallbackProvider) {
            $('#fallback-provider').value = settings.fallbackProvider;
        }
        updateProviderUI();
        loadSavedProviderSettings();
    }

    // Start translation
    startBtn.addEventListener('click', async () => {
        const p = state.provider;
        const apiKey = $('#api-key').value;
        const model = $('#model-select').value;
        const customUrl = $('#custom-url').value;
        const customModel = $('#custom-model').value;

        if (PROVIDER_NEEDS_KEY[p] && !apiKey && p !== 'custom') {
            alert('Please enter your API key\n请输入 API Key');
            return;
        }
        if (p === 'custom' && !customUrl) {
            alert('Please enter API Base URL\n请输入 API 地址');
            return;
        }

        startBtn.classList.add('loading');
        startBtn.querySelector('.btn-text').textContent = 'Starting... / 启动中...';

        const settings = loadSettings();
        const fallbackProvider = settings.fallbackProvider || "";

        try {
            const res = await fetch('/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_id: state.taskId,
                    filepath: state.filepath,
                    filename: state.filename,
                    provider: p,
                    api_key: apiKey,
                    model: model,
                    custom_url: customUrl,
                    custom_model: customModel,
                    fallback_provider: fallbackProvider,
                    fallback_api_key: getProviderSettings(fallbackProvider).apiKey || "",
                    fallback_model: getProviderSettings(fallbackProvider).model || ""
                })
            });
            const data = await res.json();

            progressSection.classList.remove('hidden');
            progressSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
            connectProgress(state.taskId);
        } catch (err) {
            alert('Failed to start: ' + err.message);
            startBtn.classList.remove('loading');
        }
    });

    function connectProgress(taskId) {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        state.ws = new WebSocket(`${protocol}//${location.host}/ws/progress/${taskId}`);
        state.ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            updateProgress(data);
            if (data.status === 'done') { state.ws.close(); loadResult(taskId); }
            else if (data.status === 'error') { state.ws.close(); alert('Error: ' + data.message); }
        };
        state.ws.onerror = () => pollProgress(taskId);
    }

    function pollProgress(taskId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${taskId}`);
                const data = await res.json();
                updateProgress(data);
                if (data.status === 'done') { clearInterval(interval); loadResult(taskId); }
                else if (data.status === 'error') { clearInterval(interval); alert('Error: ' + data.message); }
            } catch (err) {}
        }, 500);
    }

    function updateProgress(data) {
        const pct = data.percent || 0;
        const phase = data.phase || 'init';
        const msg = data.message || '';

        $('#progress-percent').textContent = pct + '%';
        const circle = $('#progress-circle');
        const circumference = 2 * Math.PI * 70;
        circle.style.strokeDashoffset = circumference - (pct / 100) * circumference;
        $('#progress-bar').style.width = pct + '%';

        const phaseLabels = {
            parsing: 'Parsing / 解析中',
            translating: 'Translating / 翻译中',
            building: 'Building EPUB / 制作中',
            done: 'Complete / 完成',
            error: 'Error / 错误'
        };
        $('#progress-phase').textContent = phaseLabels[phase] || phase;
        $('#progress-message').textContent = msg;

        const steps = ['parse', 'translate', 'build', 'done'];
        const phaseOrder = { parsing: 0, translating: 1, building: 2, done: 3, error: -1 };
        const currentIdx = phaseOrder[phase] ?? -1;
        steps.forEach((s, i) => {
            const el = $(`#step-${s}`);
            el.classList.remove('active', 'done');
            if (i < currentIdx) el.classList.add('done');
            else if (i === currentIdx) el.classList.add('active');
        });
    }

    async function loadResult(taskId) {
        setTimeout(() => {
            progressSection.classList.add('hidden');
            resultSection.classList.remove('hidden');
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
            loadStats(taskId);
        }, 800);
    }

    async function loadStats(taskId) {
        try {
            const res = await fetch(`/api/progress/${taskId}`);
            const data = await res.json();
            if (data.result) renderStats(data.result);
            else renderStats({ total_chapters: '—', total_ielts_words: '—', unique_ielts_words: '—', ielts_words_sample: [] });
        } catch (err) {}
    }

    function renderStats(stats) {
        $('#stat-chapters').textContent = stats.total_chapters || '—';
        $('#stat-ielts').textContent = stats.total_ielts_words || '—';
        $('#stat-unique').textContent = stats.unique_ielts_words || '—';

        const chips = $('#word-chips');
        chips.innerHTML = '';
        (stats.ielts_words_sample || []).forEach(w => {
            const chip = document.createElement('div');
            chip.className = 'word-chip';
            chip.innerHTML = `<span class="chip-word">${esc(w.word)}</span><span class="chip-meaning">${esc(w.meaning)}</span>`;
            chips.appendChild(chip);
        });
        if (!stats.ielts_words_sample || stats.ielts_words_sample.length === 0) {
            chips.innerHTML = '<span style="color:var(--text-dim);font-size:0.85rem">No IELTS words preview</span>';
        }
    }

    downloadBtn.addEventListener('click', () => { if (state.taskId) window.location.href = `/api/download/${state.taskId}`; });
    restartBtn.addEventListener('click', resetAll);

    function resetAll() {
        state.taskId = null; state.filepath = null; state.filename = null;
        if (state.ws) state.ws.close();
        fileInput.value = '';
        fileInfo.classList.add('hidden');
        dropZone.classList.remove('hidden');
        providerSection.classList.add('hidden');
        progressSection.classList.add('hidden');
        resultSection.classList.add('hidden');
        startBtn.classList.remove('loading');
        startBtn.querySelector('.btn-text').textContent = 'Start Translation / 开始翻译';
        $('#progress-percent').textContent = '0%';
        $('#progress-circle').style.strokeDashoffset = 2 * Math.PI * 70;
        $('#progress-bar').style.width = '0%';
        uploadSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

    // SVG gradient
    const svg = document.querySelector('.progress-ring');
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `<linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#6c63ff"/><stop offset="100%" style="stop-color:#c8a96e"/></linearGradient>`;
    svg.prepend(defs);
    $('#progress-circle').setAttribute('stroke', 'url(#progressGradient)');

    // Init
    loadDefaults();
})();
