// Global Application State
let TRANSCRIPTS_DATA = {};
let GUIDE_ANSWERS_DATA = [];
let THEMES_DATA = [];
let CURRENT_TRANSCRIPT_ID = 'Transcript_1_France';
let CURRENT_ACTIVE_TAB = 'guide';

// Initialize application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Check saved theme preference
    if (localStorage.getItem('hasamex_theme') === 'dark') {
        document.body.classList.add('dark-theme', 'dark');
        document.documentElement.classList.add('dark');
        updateThemeToggleUI(true);
    }
    fetchInitialData();
});

// Dark Mode Toggle Handler
function toggleDarkMode() {
    const isDark = document.body.classList.toggle('dark-theme');
    document.documentElement.classList.toggle('dark', isDark);
    document.body.classList.toggle('dark', isDark);
    localStorage.setItem('hasamex_theme', isDark ? 'dark' : 'light');
    updateThemeToggleUI(isDark);
}

function updateThemeToggleUI(isDark) {
    const icon = document.getElementById('theme-toggle-icon');
    const text = document.getElementById('theme-toggle-text');
    const btn = document.getElementById('theme-toggle-btn');

    if (isDark) {
        if (icon) icon.className = 'fa-solid fa-sun text-amber-400';
        if (text) text.innerText = 'Light Mode';
        if (btn) {
            btn.classList.remove('bg-slate-100', 'text-slate-700', 'border-slate-200');
            btn.classList.add('bg-neutral-900', 'text-neutral-200', 'border-neutral-800');
        }
    } else {
        if (icon) icon.className = 'fa-solid fa-moon text-violet-600';
        if (text) text.innerText = 'Dark Mode';
        if (btn) {
            btn.classList.remove('bg-neutral-900', 'text-neutral-200', 'border-neutral-800');
            btn.classList.add('bg-slate-100', 'text-slate-700', 'border-slate-200');
        }
    }
}

async function fetchInitialData() {
    try {
        const [txRes, guideRes, themeRes] = await Promise.all([
            fetch('/api/transcripts'),
            fetch('/api/guide-answers'),
            fetch('/api/themes')
        ]);

        TRANSCRIPTS_DATA = await txRes.json();
        GUIDE_ANSWERS_DATA = await guideRes.json();
        THEMES_DATA = await themeRes.json();

        const keys = Object.keys(TRANSCRIPTS_DATA);
        if (keys.length > 0 && (!CURRENT_TRANSCRIPT_ID || !TRANSCRIPTS_DATA[CURRENT_TRANSCRIPT_ID])) {
            CURRENT_TRANSCRIPT_ID = keys[0];
        }

        renderExpertScopeSidebar();
        renderTranscriptSubtabs();
        renderGuideAnswers();
        renderThemes();
        renderTranscriptViewer(CURRENT_TRANSCRIPT_ID);
    } catch (err) {
        console.error('Failed to load initial application data:', err);
    }
}

// Sidebar Navigation Handler
function switchTab(tabId) {
    CURRENT_ACTIVE_TAB = tabId;
    document.querySelectorAll('.sidebar-nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-view').forEach(view => view.classList.add('hidden'));

    const activeBtn = document.getElementById(`tab-btn-${tabId}`);
    const activeView = document.getElementById(`view-${tabId}`);

    if (activeBtn) activeBtn.classList.add('active');
    if (activeView) activeView.classList.remove('hidden');
}

// Collapsible Accordion Toggle for Interview Guide
function toggleQuestionAccordion(qIdx) {
    const content = document.getElementById(`acc-content-q-${qIdx}`);
    const icon = document.getElementById(`acc-icon-q-${qIdx}`);

    if (!content) return;
    const isHidden = content.classList.contains('hidden');

    if (isHidden) {
        content.classList.remove('hidden');
        if (icon) icon.classList.add('rotated');
    } else {
        content.classList.add('hidden');
        if (icon) icon.classList.remove('rotated');
    }
}

// Collapsible Accordion Toggle for Themes
function toggleThemeAccordion(tIdx) {
    const content = document.getElementById(`acc-content-t-${tIdx}`);
    const icon = document.getElementById(`acc-icon-t-${tIdx}`);

    if (!content) return;
    const isHidden = content.classList.contains('hidden');

    if (isHidden) {
        content.classList.remove('hidden');
        if (icon) icon.classList.add('rotated');
    } else {
        content.classList.add('hidden');
        if (icon) icon.classList.remove('rotated');
    }
}

// Render Tab 1: Interview Guide Matrix (Collapsible Accordions)
function renderGuideAnswers() {
    const container = document.getElementById('guide-questions-container');
    if (!container || !GUIDE_ANSWERS_DATA.length) return;

    const roleMap = {
        'Dr. Jean Martin': 'Head of urology',
        'Anna Keller': 'Former Procurement Director',
        'Dr. Emily Carter': 'Consultant Urologist'
    };

    container.innerHTML = GUIDE_ANSWERS_DATA.map((qItem, qIdx) => {
        const count = qItem.answers_by_expert.length;
        const isScrollable = count > 3;

        const gridOrScrollClass = isScrollable
            ? 'flex overflow-x-auto gap-6 pt-2 pb-3 custom-h-scroll max-w-full'
            : 'grid grid-cols-1 md:grid-cols-3 gap-6 pt-2';

        const cardWidthClass = isScrollable
            ? 'w-[320px] md:w-[350px] shrink-0'
            : '';

        const expertCards = qItem.answers_by_expert.map(ans => {
            const role = roleMap[ans.expert_name] || 'Expert Specialist';
            const countryBadge = ans.market;

            const evidenceHtml = ans.evidence.map(ev => `
                <div onclick="highlightQuote('${ev.transcript_id}', ${ev.segment_index})" 
                     class="quote-card-container">
                    <div class="flex items-start gap-3">
                        <span class="text-slate-400 font-serif text-xl leading-none font-bold">❞</span>
                        <div class="flex-1 space-y-2">
                            <p class="text-xs italic leading-relaxed quote-text">
                                "${ev.quote}"
                            </p>
                            <div class="flex items-center justify-between text-[11px] pt-1.5 font-medium">
                                <span class="quote-action-link flex items-center gap-1">
                                    <i class="fa-regular fa-clock"></i> ${ev.timestamp}
                                </span>
                                <span class="quote-action-link flex items-center gap-1">
                                    <span>Jump to line</span> <i class="fa-solid fa-arrow-right"></i>
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

            return `
                <div class="expert-card p-6 md:p-7 flex flex-col justify-between space-y-5 ${cardWidthClass}">
                    <div>
                        <div class="flex items-start justify-between mb-3.5 expert-card-header pb-3.5">
                            <div>
                                <h4 class="font-bold text-sm md:text-base leading-tight tracking-tight">${ans.expert_name}</h4>
                                <p class="text-xs font-medium text-slate-500 mt-0.5">${role}</p>
                            </div>
                            <span class="country-pill text-xs font-semibold px-3 py-1 rounded-full shadow-2xs">${countryBadge}</span>
                        </div>
                        <p class="text-xs md:text-[13px] font-semibold leading-relaxed pt-1 mb-3">
                            ${ans.answer}
                        </p>
                    </div>
                    <div>
                        ${evidenceHtml}
                    </div>
                </div>
            `;
        }).join('');

        const isFirstOpen = qIdx === 0 ? '' : 'hidden';
        const iconRotated = qIdx === 0 ? 'rotated' : '';

        return `
            <div class="glass-panel border shadow-lg overflow-hidden transition-all">
                <!-- Accordion Header -->
                <div onclick="toggleQuestionAccordion(${qIdx})" class="p-6 md:p-7 cursor-pointer flex items-center justify-between gap-4 hover:bg-slate-500/5 transition">
                    <div class="flex items-center gap-3.5">
                        <span class="w-8 h-8 rounded-xl bg-violet-600/10 text-violet-600 font-bold flex items-center justify-center text-xs shrink-0 border border-violet-600/20">
                            Q${qIdx + 1}
                        </span>
                        <h3 class="font-bold text-base md:text-lg leading-snug tracking-tight">${qItem.question}</h3>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="text-xs text-slate-400 font-medium hidden sm:inline">${count} Expert Responses</span>
                        <div class="w-8 h-8 rounded-full accordion-chevron-btn flex items-center justify-center shrink-0">
                            <i id="acc-icon-q-${qIdx}" class="fa-solid fa-chevron-down accordion-icon text-xs ${iconRotated}"></i>
                        </div>
                    </div>
                </div>
                <!-- Accordion Body -->
                <div id="acc-content-q-${qIdx}" class="p-6 md:p-7 pt-0 accordion-divider ${isFirstOpen}">
                    <div class="pt-5 space-y-5">
                        <!-- Executive Takeaway (Clean typography inline summary) -->
                        <div class="p-4 rounded-2xl bg-violet-500/5 dark:bg-violet-500/10 border border-violet-500/15 mb-2">
                            <p class="text-xs md:text-sm font-medium leading-relaxed text-slate-800 dark:text-slate-200">
                                <strong class="text-violet-600 dark:text-violet-400 font-bold">Executive Takeaway:</strong> ${qItem.overall_summary || 'Executive cross-market synthesis across all expert responses.'}
                            </p>
                        </div>

                        <!-- Per-Expert Cards Container (Grid if <=3, Scrollable Row if >3) -->
                        <div class="${gridOrScrollClass}">
                            ${expertCards}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Render Tab 2: Themes & Disagreements (Collapsible Accordions)
function renderThemes() {
    const container = document.getElementById('themes-container');
    if (!container || !THEMES_DATA.length) return;

    container.innerHTML = THEMES_DATA.map((t, tIdx) => {
        const isConsensus = t.type === 'consensus';
        const badgeClass = isConsensus 
            ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/30' 
            : 'bg-coral-600/10 text-coral-600 border-coral-600/30';
        const badgeIcon = isConsensus ? 'fa-handshake' : 'fa-code-compare';
        const badgeLabel = isConsensus ? 'Consensus Theme' : 'Market Disagreement';

        const evidenceHtml = t.evidence.map(ev => `
            <div onclick="highlightQuote('${ev.transcript_id}', ${ev.segment_index})"
                 class="quote-card-container">
                <div class="flex items-center justify-between text-xs font-semibold mb-1.5">
                    <span class="quote-meta">${ev.market} (${ev.expert_name})</span>
                    <span class="country-pill px-2.5 py-0.5 rounded-md text-[10px] font-mono">
                        ${ev.timestamp}
                    </span>
                </div>
                <p class="text-xs italic leading-relaxed quote-text">"${ev.quote}"</p>
                <div class="mt-1.5 text-[10px] quote-action-link text-right flex items-center justify-end gap-1 font-semibold">
                    <span>Inspect in transcript</span> <i class="fa-solid fa-arrow-right"></i>
                </div>
            </div>
        `).join('');

        const isFirstOpen = tIdx < 2 ? '' : 'hidden';
        const iconRotated = tIdx < 2 ? 'rotated' : '';

        return `
            <div class="glass-panel border shadow-md overflow-hidden transition-all">
                <!-- Accordion Header -->
                <div onclick="toggleThemeAccordion(${tIdx})" class="p-6 md:p-7 cursor-pointer flex items-center justify-between gap-4 hover:bg-slate-500/5 transition">
                    <div class="flex items-center gap-3.5">
                        <h4 class="font-bold text-base md:text-lg leading-snug tracking-tight">${t.topic}</h4>
                        <span class="px-3.5 py-1 rounded-full border text-xs font-semibold flex items-center gap-1.5 shrink-0 ${badgeClass}">
                            <i class="fa-solid ${badgeIcon}"></i> ${badgeLabel}
                        </span>
                    </div>
                    <div class="w-8 h-8 rounded-full accordion-chevron-btn flex items-center justify-center shrink-0">
                        <i id="acc-icon-t-${tIdx}" class="fa-solid fa-chevron-down accordion-icon text-xs ${iconRotated}"></i>
                    </div>
                </div>
                <!-- Accordion Body -->
                <div id="acc-content-t-${tIdx}" class="p-6 md:p-7 pt-0 accordion-divider ${isFirstOpen}">
                    <div class="pt-5 space-y-5">
                        <p class="text-xs md:text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">${t.summary}</p>
                        <div class="pt-4 accordion-divider space-y-3">
                            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Cross-Market Extracted Quotes</span>
                            <div class="space-y-3">
                                ${evidenceHtml}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Render Tab 3: Transcript Viewer
function renderTranscriptViewer(transcriptId) {
    CURRENT_TRANSCRIPT_ID = transcriptId;
    renderTranscriptSubtabs();

    const reader = document.getElementById('transcript-reader');
    if (!reader) return;

    const data = TRANSCRIPTS_DATA[transcriptId];
    if (!data) {
        reader.innerHTML = `<p class="text-slate-500 text-sm">Transcript data loading...</p>`;
        return;
    }

    const segments = data.segments;
    reader.innerHTML = segments.map(seg => {
        const isInterviewer = seg.speaker.toLowerCase().includes('interviewer');
        const speakerColor = isInterviewer ? 'text-slate-500 font-medium' : 'text-violet-600 font-bold';
        const cardBg = isInterviewer ? 'bg-white/50 border-white/80' : 'bg-white border-slate-200/80 shadow-xs';

        return `
            <div id="segment-${transcriptId}-${seg.segment_index}" 
                 class="segment-card p-4.5 md:p-5 rounded-2xl border ${cardBg} space-y-2">
                <div class="flex items-center justify-between text-xs mb-1.5">
                    <span class="${speakerColor}">${seg.speaker}</span>
                    <span class="country-pill px-2.5 py-0.5 rounded-md font-mono text-[10px]">
                        ${seg.timestamp}
                    </span>
                </div>
                <p class="text-xs md:text-sm font-medium leading-relaxed">${seg.text}</p>
            </div>
        `;
    }).join('');
}

function switchTranscript(transcriptId) {
    renderTranscriptViewer(transcriptId);
}

function filterTranscriptSegments() {
    const query = document.getElementById('transcript-search').value.toLowerCase().trim();
    const data = TRANSCRIPTS_DATA[CURRENT_TRANSCRIPT_ID];
    if (!data) return;

    data.segments.forEach(seg => {
        const el = document.getElementById(`segment-${CURRENT_TRANSCRIPT_ID}-${seg.segment_index}`);
        if (!el) return;
        const matches = seg.text.toLowerCase().includes(query) || seg.speaker.toLowerCase().includes(query);
        el.style.display = matches ? 'block' : 'none';
    });
}

// Click-to-Scroll & Yellow Highlight Pulse Handler
function highlightQuote(transcriptId, segmentIndex) {
    closeChatPopover();
    switchTab('viewer');
    renderTranscriptViewer(transcriptId);

    setTimeout(() => {
        const targetId = `segment-${transcriptId}-${segmentIndex}`;
        const el = document.getElementById(targetId);

        if (!el) {
            console.warn(`Could not find DOM element #${targetId}`);
            return;
        }

        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('highlight-pulse');
        setTimeout(() => el.classList.remove('highlight-pulse'), 2500);
    }, 140);
}

// Floating RAG Chat Submit Handler (Entire Quote Cards Clickable)
async function handleChatSubmit(event) {
    event.preventDefault();
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question) return;

    const submitBtn = document.getElementById('chat-submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-xs"></i>`;

    const popover = document.getElementById('chat-popover');
    const backdrop = document.getElementById('chat-backdrop');
    const body = document.getElementById('chat-popover-body');
    const title = document.getElementById('chat-popover-title');
    const citationsList = document.getElementById('chat-citations-list');

    title.innerText = `RAG Vector Search: "${question}"`;
    body.innerHTML = `<div class="text-slate-500 font-medium animate-pulse flex items-center gap-2"><i class="fa-solid fa-circle-notch animate-spin text-violet-600"></i> Querying ChromaDB vectors across France, Germany, and UK...</div>`;
    citationsList.innerHTML = '';

    // Show popover & glass backdrop blur
    popover.classList.remove('hidden');
    if (backdrop) backdrop.classList.remove('hidden');

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        const data = await res.json();

        // 1. Render Markdown using Marked.js
        let parsedHtml = (typeof marked !== 'undefined' && marked.parse)
            ? marked.parse(data.answer)
            : data.answer.replace(/\n/g, '<br>');

        // 2. Post-process to make timestamps inline clickable
        if (data.evidence && data.evidence.length) {
            data.evidence.forEach(ev => {
                const tsStr = ev.timestamp;
                const pattern = new RegExp(`\\b(${tsStr})\\b`, 'g');
                parsedHtml = parsedHtml.replace(pattern, `<button onclick="highlightQuote('${ev.transcript_id}', ${ev.segment_index})" class="inline-timestamp-link"><i class="fa-regular fa-clock text-[9px]"></i> ${ev.timestamp}</button>`);
            });
        }

        body.innerHTML = parsedHtml;

        // Render Entire Quote Cards Clickable at bottom of RAG popover
        if (data.evidence && data.evidence.length) {
            citationsList.innerHTML = data.evidence.map(ev => `
                <div onclick="highlightQuote('${ev.transcript_id}', ${ev.segment_index})" 
                     class="quote-card-container text-left w-full my-1.5 transition">
                    <div class="flex items-center justify-between text-xs font-bold quote-meta mb-1">
                        <span>${ev.market} (${ev.expert_name})</span>
                        <span class="country-pill px-2 py-0.5 rounded text-[10px] font-mono">${ev.timestamp}</span>
                    </div>
                    <p class="text-xs quote-text italic leading-relaxed my-1">"${ev.quote}"</p>
                    <div class="text-[10px] quote-action-link font-bold text-right mt-1.5 flex items-center justify-end gap-1">
                        <span>Click quote to jump to transcript line</span> <i class="fa-solid fa-arrow-right"></i>
                    </div>
                </div>
            `).join('');
        } else {
            citationsList.innerHTML = `<span class="text-xs text-slate-500 font-medium">No specific citations returned.</span>`;
        }
    } catch (err) {
        body.innerHTML = `<p class="text-rose-600 font-medium">Error processing RAG query. Please check server logs.</p>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="fa-solid fa-arrow-up text-xs"></i>`;
        input.value = '';
    }
}

function closeChatPopover() {
    const popover = document.getElementById('chat-popover');
    const backdrop = document.getElementById('chat-backdrop');
    if (popover) popover.classList.add('hidden');
    if (backdrop) backdrop.classList.add('hidden');
}

// Dynamic Sidebar Expert Scope List
function renderExpertScopeSidebar() {
    const container = document.getElementById('expert-scope-list');
    if (!container) return;

    const keys = Object.keys(TRANSCRIPTS_DATA);
    container.innerHTML = keys.map(tid => {
        const meta = TRANSCRIPTS_DATA[tid].metadata;
        return `
            <div class="flex items-center justify-between border-b border-slate-200/50 dark:border-neutral-800 pb-1.5 pt-0.5 text-[11px] gap-2">
                <span class="font-medium text-slate-600 dark:text-slate-400 shrink-0 whitespace-nowrap">${meta.market}:</span> 
                <span class="font-semibold text-slate-800 dark:text-slate-200 truncate text-right">${meta.expert_name}</span>
            </div>
        `;
    }).join('');
}

// Dynamic Transcript Viewer Subtabs
function renderTranscriptSubtabs() {
    const container = document.getElementById('transcript-subtabs-container');
    if (!container) return;

    const flagMap = {
        'France': '🇫🇷',
        'Germany': '🇩🇪',
        'United Kingdom': '🇬🇧',
        'UK': '🇬🇧',
        'Spain': '🇪🇸',
        'Italy': '🇮🇹'
    };

    const keys = Object.keys(TRANSCRIPTS_DATA);
    container.innerHTML = keys.map(tid => {
        const meta = TRANSCRIPTS_DATA[tid].metadata;
        const flag = flagMap[meta.market] || '🌐';
        const isActive = tid === CURRENT_TRANSCRIPT_ID ? 'active' : '';

        return `
            <button onclick="switchTranscript('${tid}')" id="tx-btn-${tid}" class="tx-subtab ${isActive} px-4 py-2 rounded-xl text-xs font-bold transition">
                ${flag} ${meta.market} (${meta.expert_name})
            </button>
        `;
    }).join('');
}

// Dynamic Transcript File Upload Handlers
let SELECTED_UPLOAD_FILE = null;

function openUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) modal.classList.remove('hidden');
    resetUploadForm();
}

function closeUploadModal() {
    const modal = document.getElementById('upload-modal');
    if (modal) modal.classList.add('hidden');
    resetUploadForm();
}

function resetUploadForm() {
    SELECTED_UPLOAD_FILE = null;
    const fileInput = document.getElementById('transcript-file-input');
    if (fileInput) fileInput.value = '';
    const submitBtn = document.getElementById('upload-submit-btn');
    if (submitBtn) submitBtn.disabled = true;
    const statusDiv = document.getElementById('upload-status');
    if (statusDiv) statusDiv.className = 'hidden';
    const title = document.getElementById('upload-dropzone-title');
    if (title) title.innerText = 'Click to browse or drag & drop transcript .txt';
    const dropzone = document.getElementById('upload-dropzone');
    if (dropzone) dropzone.classList.remove('drag-over');
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    const dropzone = document.getElementById('upload-dropzone');
    if (dropzone) dropzone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    const dropzone = document.getElementById('upload-dropzone');
    if (dropzone) dropzone.classList.remove('drag-over');
}

function handleFileDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    const dropzone = document.getElementById('upload-dropzone');
    if (dropzone) dropzone.classList.remove('drag-over');

    const files = e.dataTransfer ? e.dataTransfer.files : null;
    if (files && files.length > 0) {
        processSelectedFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files && files.length > 0) {
        processSelectedFile(files[0]);
    }
}

function processSelectedFile(file) {
    if (!file.name.endsWith('.txt')) {
        showUploadStatus('Error: Only .txt transcript files are supported.', true);
        return;
    }
    SELECTED_UPLOAD_FILE = file;
    const title = document.getElementById('upload-dropzone-title');
    if (title) title.innerHTML = `<span class="text-violet-600 font-bold">${file.name}</span> (${(file.size / 1024).toFixed(1)} KB)`;
    const submitBtn = document.getElementById('upload-submit-btn');
    if (submitBtn) submitBtn.disabled = false;
    showUploadStatus(`File selected: ${file.name}. Click 'Upload & Index' to process.`, false);
}

function showUploadStatus(msg, isError = false) {
    const statusDiv = document.getElementById('upload-status');
    if (!statusDiv) return;
    statusDiv.classList.remove('hidden');
    if (isError) {
        statusDiv.className = 'text-xs font-medium p-3 rounded-xl bg-rose-500/10 text-rose-600 border border-rose-500/20';
    } else {
        statusDiv.className = 'text-xs font-medium p-3 rounded-xl bg-violet-600/10 text-violet-600 border border-violet-600/20';
    }
    statusDiv.innerText = msg;
}

async function submitTranscriptUpload() {
    if (!SELECTED_UPLOAD_FILE) return;

    const submitBtn = document.getElementById('upload-submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> Uploading...`;

    showUploadStatus(`Parsing transcript and indexing vectors into ChromaDB...`, false);

    const formData = new FormData();
    formData.append('file', SELECTED_UPLOAD_FILE);

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (res.ok && data.success) {
            showUploadStatus(`Success! Uploaded ${data.market} (${data.expert_name}) - ${data.segment_count} dialogue segments indexed.`, false);
            setTimeout(async () => {
                closeUploadModal();
                await fetchInitialData();
                if (data.transcript_id) {
                    switchTab('viewer');
                    switchTranscript(data.transcript_id);
                }
            }, 1200);
        } else {
            showUploadStatus(data.error || 'Upload failed. Please check transcript file format.', true);
            submitBtn.disabled = false;
            submitBtn.innerHTML = `Upload & Index`;
        }
    } catch (err) {
        showUploadStatus(`Network error during upload: ${err.message}`, true);
        submitBtn.disabled = false;
        submitBtn.innerHTML = `Upload & Index`;
    }
}
