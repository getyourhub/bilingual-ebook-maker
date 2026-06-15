(() => {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const state = {
        taskId: null,
        filepath: null,
        filename: null,
        ws: null
    };

    // Elements
    const dropZone = $('#drop-zone');
    const fileInput = $('#file-input');
    const browseBtn = $('#browse-btn');
    const fileInfo = $('#file-info');
    const fileName = $('#file-name');
    const fileMeta = $('#file-meta');
    const removeFile = $('#remove-file');
    const uploadSection = $('#upload-section');
    const translateSection = $('#translate-section');
    const progressSection = $('#progress-section');
    const resultSection = $('#result-section');
    const startBtn = $('#start-btn');
    const downloadBtn = $('#download-btn');
    const restartBtn = $('#restart-btn');
    const previewTitle = $('#preview-title');
    const previewAuthor = $('#preview-author');

    // Drag & drop
    ['dragenter', 'dragover'].forEach(e => {
        dropZone.addEventListener(e, (ev) => {
            ev.preventDefault();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(e => {
        dropZone.addEventListener(e, (ev) => {
            ev.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) handleFile(files[0]);
    });

    dropZone.addEventListener('click', () => fileInput.click());
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });

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

            if (data.error) {
                alert(data.error);
                return;
            }

            state.taskId = data.task_id;
            state.filepath = data.filepath;
            state.filename = data.filename;

            fileName.textContent = data.filename;
            fileMeta.textContent = `${data.book_info.type} · ${data.book_info.author}`;

            fileInfo.classList.remove('hidden');
            dropZone.classList.add('hidden');

            previewTitle.textContent = data.book_info.title;
            previewAuthor.textContent = data.book_info.author;

            translateSection.classList.remove('hidden');
            translateSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

        } catch (err) {
            alert('Upload failed: ' + err.message);
        }
    }

    startBtn.addEventListener('click', async () => {
        startBtn.classList.add('loading');
        startBtn.querySelector('.btn-text').textContent = 'Starting... / 启动中...';

        try {
            const res = await fetch('/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_id: state.taskId,
                    filepath: state.filepath,
                    filename: state.filename
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
        const wsUrl = `${protocol}//${location.host}/ws/progress/${taskId}`;

        state.ws = new WebSocket(wsUrl);

        state.ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            updateProgress(data);

            if (data.status === 'done') {
                state.ws.close();
                loadResult(taskId);
            } else if (data.status === 'error') {
                state.ws.close();
                alert('Error: ' + data.message);
            }
        };

        state.ws.onerror = () => {
            pollProgress(taskId);
        };
    }

    function pollProgress(taskId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${taskId}`);
                const data = await res.json();
                updateProgress(data);

                if (data.status === 'done') {
                    clearInterval(interval);
                    loadResult(taskId);
                } else if (data.status === 'error') {
                    clearInterval(interval);
                    alert('Error: ' + data.message);
                }
            } catch (err) { /* retry */ }
        }, 500);
    }

    function updateProgress(data) {
        const pct = data.percent || 0;
        const phase = data.phase || 'init';
        const msg = data.message || '';

        // Update percent text
        $('#progress-percent').textContent = pct + '%';

        // Update progress ring
        const circle = $('#progress-circle');
        const circumference = 2 * Math.PI * 70; // r=70
        circle.style.strokeDashoffset = circumference - (pct / 100) * circumference;

        // Update bar
        $('#progress-bar').style.width = pct + '%';

        // Update text
        const phaseLabels = {
            parsing: 'Parsing / 解析中',
            translating: 'Translating / 翻译中',
            building: 'Building EPUB / 制作中',
            done: 'Complete / 完成',
            error: 'Error / 错误'
        };
        $('#progress-phase').textContent = phaseLabels[phase] || phase;
        $('#progress-message').textContent = msg;

        // Update step indicators
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
        try {
            const res = await fetch(`/api/progress/${taskId}`);
            const data = await res.json();

            // Fetch detailed result
            const detailRes = await fetch(`/api/download/${taskId}`, { method: 'HEAD' });

            // Show result section
            setTimeout(() => {
                progressSection.classList.add('hidden');
                resultSection.classList.remove('hidden');
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // We get stats from a separate call or reconstruct
                loadStats(taskId);
            }, 800);

        } catch (err) {
            console.error(err);
        }
    }

    async function loadStats(taskId) {
        // Poll once more to get full stats from progress manager
        try {
            const res = await fetch(`/api/progress/${taskId}`);
            const data = await res.json();

            // Stats may be embedded after completion
            if (data.result) {
                renderStats(data.result);
            } else {
                // Placeholder stats
                renderStats({
                    total_chapters: '—',
                    total_ielts_words: '—',
                    unique_ielts_words: '—',
                    ielts_words_sample: []
                });
            }
        } catch (err) {
            console.error(err);
        }
    }

    function renderStats(stats) {
        $('#stat-chapters').textContent = stats.total_chapters || '—';
        $('#stat-ielts').textContent = stats.total_ielts_words || '—';
        $('#stat-unique').textContent = stats.unique_ielts_words || '—';

        const chips = $('#word-chips');
        chips.innerHTML = '';
        const sample = stats.ielts_words_sample || [];
        sample.forEach(w => {
            const chip = document.createElement('div');
            chip.className = 'word-chip';
            chip.innerHTML = `<span class="chip-word">${esc(w.word)}</span><span class="chip-meaning">${esc(w.meaning)}</span>`;
            chips.appendChild(chip);
        });

        if (sample.length === 0) {
            chips.innerHTML = '<span style="color:var(--text-dim);font-size:0.85rem">No IELTS words preview available</span>';
        }
    }

    downloadBtn.addEventListener('click', () => {
        if (state.taskId) {
            window.location.href = `/api/download/${state.taskId}`;
        }
    });

    restartBtn.addEventListener('click', resetAll);

    function resetAll() {
        state.taskId = null;
        state.filepath = null;
        state.filename = null;
        if (state.ws) state.ws.close();

        fileInput.value = '';
        fileInfo.classList.add('hidden');
        dropZone.classList.remove('hidden');
        translateSection.classList.add('hidden');
        progressSection.classList.add('hidden');
        resultSection.classList.add('hidden');

        startBtn.classList.remove('loading');
        startBtn.querySelector('.btn-text').textContent = 'Start Translation / 开始翻译';

        // Reset progress visuals
        $('#progress-percent').textContent = '0%';
        const circle = $('#progress-circle');
        circle.style.strokeDashoffset = 2 * Math.PI * 70;
        $('#progress-bar').style.width = '0%';

        uploadSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    // Add SVG gradient definition for progress ring
    const svg = document.querySelector('.progress-ring');
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
        <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#6c63ff"/>
            <stop offset="100%" style="stop-color:#c8a96e"/>
        </linearGradient>
    `;
    svg.prepend(defs);

    // Update progress ring to use gradient
    const circle = $('#progress-circle');
    circle.setAttribute('stroke', 'url(#progressGradient)');
})();
