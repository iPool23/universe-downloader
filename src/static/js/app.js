/**
 * Universe Downloader - Client Side Application
 * 
 * @author Pool Anthony Deza Millones
 * @github @iPool23
 * @version 3.0.0
 */

let selectedFormat = 'mp4';
let selectedQuality = null;
let selectedAudioQuality = 192; // Por defecto 192kbps
let availableQualities = [];

// Theme Handling
const themeSwitch = document.getElementById('themeSwitch');
const userTheme = localStorage.getItem('theme');
const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

// Initial State
if (userTheme === 'dark' || (!userTheme && systemDark)) {
    document.body.classList.add('dark-mode');
    if (themeSwitch) themeSwitch.checked = true;
} else {
    document.body.classList.remove('dark-mode');
    if (themeSwitch) themeSwitch.checked = false;
}

// Toggle Listener
if (themeSwitch) {
    themeSwitch.addEventListener('change', function (e) {
        if (e.target.checked) {
            document.body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
        }
    });
}

// Calidades de audio disponibles
const audioQualities = [
    { value: 320, label: '320 kbps (Máxima)' },
    { value: 256, label: '256 kbps (Alta)' },
    { value: 192, label: '192 kbps (Normal)' },
    { value: 128, label: '128 kbps (Baja)' }
];

// Manejo de botones de formato
document.querySelectorAll('.format-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        selectedFormat = this.dataset.format;

        // Mostrar/ocultar selectores de calidad según el formato
        const videoQualityContainer = document.getElementById('videoQualityContainer');
        const audioQualityContainer = document.getElementById('audioQualityContainer');

        if (videoQualityContainer && audioQualityContainer) {
            if (selectedFormat === 'mp4') {
                videoQualityContainer.style.display = 'flex';
                audioQualityContainer.style.display = 'none';
            } else {
                videoQualityContainer.style.display = 'none';
                audioQualityContainer.style.display = 'flex';
            }
        }
    });
});

// Navigation Logic
const appFeatures = window.APP_FEATURES || { rembg: true, outpaint: true, ffmpeg: true };
const rembgEnabled = appFeatures.rembg !== false;
const outpaintEnabled = appFeatures.outpaint !== false;
const ffmpegEnabled = appFeatures.ffmpeg !== false;

if (!outpaintEnabled) {
    document.querySelectorAll('[data-view="outpaintView"], #outpaintView').forEach((element) => element.remove());
}

if (!rembgEnabled) {
    document.querySelectorAll('[data-view="rembgView"], #rembgView').forEach((element) => element.remove());
}

// Sin FFmpeg, casi ninguna descarga de video moderna funciona (YouTube separa video y audio
// en streams distintos) — se avisa antes de que la persona pierda tiempo intentándolo.
if (!ffmpegEnabled) {
    const banner = document.getElementById('ffmpegBanner');
    if (banner) banner.style.display = 'flex';
}

const navItems = document.querySelectorAll('.nav-item');
const allViews = ['downloaderView', 'imageConverterView', 'converterView', 'audioExtractView', 'pdfCompressView'];

if (outpaintEnabled) allViews.push('outpaintView');
if (rembgEnabled) allViews.push('rembgView');

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();

        const targetView = item.getAttribute('data-view');
        if (!targetView) return;

        // Visual Active State
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        const viewTitle = document.getElementById('viewTitle');
        if (viewTitle) viewTitle.textContent = item.dataset.title || item.textContent.trim();

        // Hide all views, show target
        allViews.forEach(viewId => {
            const view = document.getElementById(viewId);
            if (view) view.style.display = viewId === targetView ? 'block' : 'none';
        });
    });
});

// =====================================================
// UPLOAD & CONVERSION LOGIC
// =====================================================

let selectedVideoFile = null;
let selectedVideoBatch = [];

// Initialize after page load
document.addEventListener('DOMContentLoaded', () => {
    // Pega el enlace y presiona Enter para escanear, sin necesidad de hacer clic en "Escanear"
    const urlInput = document.getElementById('url');
    if (urlInput) {
        urlInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.keyCode === 13) {
                e.preventDefault();
                scanVideo();
            }
        });
    }

    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('videoFileInput');

    if (uploadZone && fileInput) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Highlight drop zone
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => uploadZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => uploadZone.classList.remove('dragover'), false);
        });

        // Handle dropped files
        uploadZone.addEventListener('drop', (e) => {
            uploadZone.classList.remove('dragover');
            let dt = e.dataTransfer;
            handleFiles(dt.files);
        });

        // Handle file input change
        fileInput.addEventListener('change', function () {
            handleFiles(this.files);
        });
    }

    const audioUploadZone = document.getElementById('audioUploadZone');
    const audioFileInput = document.getElementById('audioFileInput');

    if (audioUploadZone && audioFileInput) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            audioUploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            audioUploadZone.addEventListener(eventName, () => audioUploadZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            audioUploadZone.addEventListener(eventName, () => audioUploadZone.classList.remove('dragover'), false);
        });

        audioUploadZone.addEventListener('drop', (e) => {
            audioUploadZone.classList.remove('dragover');
            handleAudioFiles(e.dataTransfer.files);
        });

        audioFileInput.addEventListener('change', function () {
            handleAudioFiles(this.files);
        });
    }
});

function handleFiles(files) {
    if (files.length === 0) return;

    const validExts = ['.mp4', '.mkv', '.avi', '.mov', '.webm'];
    const valid = [];
    for (const file of Array.from(files)) {
        const filename = file.name.toLowerCase();
        if (file.size > 500 * 1024 * 1024) {
            showModal('error', 'alert-circle', 'Error', `${file.name} supera el límite de 500MB`);
            continue;
        }
        if (!validExts.some(ext => filename.endsWith(ext))) {
            showModal('error', 'alert-circle', 'Error', `${file.name}: formato no soportado. Usa MP4, MKV, AVI, MOV o WEBM.`);
            continue;
        }
        valid.push(file);
    }
    if (valid.length === 0) return;

    if (valid.length === 1) {
        handleSingleVideoSelection(valid[0]);
    } else {
        handleVideoBatchSelection(valid);
    }
}

function handleSingleVideoSelection(file) {
    selectedVideoFile = file;
    selectedVideoBatch = [];
    document.getElementById('videoBatchList').style.display = 'none';

    const title = document.getElementById('uploadTitle');
    const subtitle = document.getElementById('uploadSubtitle');
    const btn = document.getElementById('uploadConvertBtn');

    title.innerHTML = `<i data-lucide="file-video" style="width: 24px; vertical-align: middle;"></i> ${file.name}`;
    subtitle.innerHTML = `${(file.size / (1024 * 1024)).toFixed(1)} MB - Listo para convertir`;

    btn.classList.remove('disabled-btn');
    btn.innerText = 'Subir y Convertir a H.264';
    btn.onclick = uploadAndConvert;

    lucide.createIcons();
}

function handleVideoBatchSelection(files) {
    selectedVideoFile = null;
    selectedVideoBatch = files;

    const title = document.getElementById('uploadTitle');
    const subtitle = document.getElementById('uploadSubtitle');
    const btn = document.getElementById('uploadConvertBtn');
    const list = document.getElementById('videoBatchList');

    const totalMB = (files.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024)).toFixed(1);
    title.innerHTML = `<i data-lucide="files" style="width: 24px; vertical-align: middle;"></i> ${files.length} videos seleccionados`;
    subtitle.innerHTML = `${totalMB} MB en total - se convierten uno por uno`;

    list.style.display = 'flex';
    list.innerHTML = files.map((file, i) => `
        <li class="file-item" id="videoBatchItem${i}">
            <div class="file-icon"><i data-lucide="file-video" style="width:18px;height:18px;"></i></div>
            <div class="file-info">
                <div class="file-name">${file.name}</div>
                <div class="file-meta"><span>${(file.size / (1024 * 1024)).toFixed(1)} MB</span></div>
            </div>
            <span class="img-batch-status" id="videoBatchStatus${i}">Pendiente</span>
        </li>`).join('');

    btn.classList.remove('disabled-btn');
    btn.innerText = `Convertir todos (${files.length})`;
    btn.onclick = uploadAndConvertBatch;

    lucide.createIcons();
}

function resetUploadZone() {
    selectedVideoFile = null;
    selectedVideoBatch = [];
    const title = document.getElementById('uploadTitle');
    const subtitle = document.getElementById('uploadSubtitle');
    const btn = document.getElementById('uploadConvertBtn');
    const list = document.getElementById('videoBatchList');

    title.innerHTML = 'Haz clic o arrastra uno o más archivos aquí';
    subtitle.innerHTML = 'Formatos soportados: MP4, WEBM, MKV, AVI, MOV (Máx 500MB c/u) · puedes elegir varios a la vez';

    btn.classList.add('disabled-btn');
    btn.innerText = 'Selecciona un archivo primero';
    btn.onclick = uploadAndConvert;
    list.style.display = 'none';
    list.innerHTML = '';
    document.getElementById('videoFileInput').value = '';
}

async function scanVideo() {
    const url = document.getElementById('url').value;
    const scanBtn = document.getElementById('scanBtn');
    const videoInfo = document.getElementById('videoInfo');

    if (!url) {
        showModal('error', 'alert-circle', 'Error', 'Por favor ingresa una URL válida');
        return;
    }

    scanBtn.disabled = true;
    scanBtn.innerHTML = '<i data-lucide="loader-2" class="spin-anim" style="width: 16px"></i> Escaneando...';
    lucide.createIcons();
    videoInfo.style.display = 'none';

    try {
        const response = await fetch(`/api/scan?url=${encodeURIComponent(url)}`);
        if (!response.ok) {
            let message = 'No se pudo obtener la información del video';
            try {
                const errorData = await response.json();
                if (typeof errorData.detail === 'string' && errorData.detail.trim()) {
                    message = errorData.detail;
                }
            } catch (_) {
                // Si el servidor no devuelve JSON, conservar el mensaje genérico.
            }
            throw new Error(message);
        }

        const data = await response.json();

        // Determine start placeholder based on duration format
        const formattedDuration = formatTime(data.duration);
        const hasHours = formattedDuration.split(':').length === 3;
        const startPlaceholder = hasHours ? "00:00:00" : "00:00";
        const timeLabel = hasHours ? "(H:MM:SS)" : "(MM:SS)";

        const thumbnailHtml = data.thumbnail
            ? `<img src="${data.thumbnail}" class="video-thumb" alt="Thumbnail">`
            : `<div class="video-thumb-placeholder"><i data-lucide="image" style="width: 48px; height: 48px; color: #666;"></i></div>`;

        // Guardar calidades disponibles
        availableQualities = data.qualities || [];
        selectedQuality = availableQualities.length > 0 ? availableQualities[0].value : null;
        selectedAudioQuality = 192; // Reset al valor por defecto

        // Generar opciones de calidad de video
        const qualityOptionsHtml = availableQualities.map((q, index) =>
            `<option value="${q.value}" ${index === 0 ? 'selected' : ''}>${q.label}</option>`
        ).join('');

        // Generar opciones de calidad de audio
        const audioQualityOptionsHtml = audioQualities.map((q) =>
            `<option value="${q.value}" ${q.value === 192 ? 'selected' : ''}>${q.label}</option>`
        ).join('');

        videoInfo.innerHTML = `
                <div class="video-details">
                <div class="thumb-container">
                    ${thumbnailHtml}
                </div>
                <div class="video-meta">
                    <h3 title="${data.title}">${data.title}</h3>
                    <p><i data-lucide="clock" style="width: 14px;"></i> ${formattedDuration}</p>
                </div>
            </div >
                <div id="videoQualityContainer" class="quality-selector-container" style="display: flex;">
                    <span class="quality-label"><i data-lucide="settings-2" style="width: 14px;"></i> Calidad:</span>
                    <select id="qualitySelect" class="quality-select" onchange="selectedQuality = parseInt(this.value)">
                        ${qualityOptionsHtml}
                    </select>
                </div>
                <div id="audioQualityContainer" class="quality-selector-container" style="display: none;">
                    <span class="quality-label"><i data-lucide="music" style="width: 14px;"></i> Calidad Audio:</span>
                    <select id="audioQualitySelect" class="quality-select" onchange="selectedAudioQuality = parseInt(this.value)">
                        ${audioQualityOptionsHtml}
                    </select>
                </div>
                <div class="time-range-container">
                    <span class="time-range-label"><i data-lucide="scissors" style="width: 14px; margin-bottom: -6px;"></i> Recortar (opcional)</span>
                    <div class="time-inputs">
                        <div class="time-input-group">
                            <label>Inicio ${timeLabel}</label>
                            <input type="text" id="startTime" placeholder="${startPlaceholder}" onblur="formatTimeInput(this)" />
                        </div>
                        <span class="arrow-icon"><i data-lucide="arrow-right"></i></span>
                        <div class="time-input-group">
                            <label>Fin ${timeLabel}</label>
                            <input type="text" id="endTime" placeholder="${formattedDuration}" onblur="formatTimeInput(this)" />
                        </div>
                    </div>
                    <p class="time-range-hint">Para bajar solo una parte, escribe hasta dónde (y desde dónde, si no es desde el principio). Solo se descarga ese tramo. Si dejas los dos vacíos, se descarga el video completo.</p>
                </div>
            `;
        videoInfo.style.display = 'block';
        lucide.createIcons();

    } catch (error) {
        showModal('error', 'x-circle', 'No se pudo leer el video', error.message);
    } finally {
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<i data-lucide="search" style="width: 16px"></i> Escanear';
        lucide.createIcons();
    }
}

function formatTimeInput(input) {
    let value = input.value.trim();
    if (!value) return;

    // Check if it's just seconds (numeric)
    if (/^\d+$/.test(value)) {
        const seconds = parseInt(value, 10);
        input.value = formatTime(seconds).trim(); // Reuse existing formatTime
        return;
    }

    // Check if colon format but ensure padding (e.g. 1:5 -> 01:05)
    if (value.includes(':')) {
        const parts = value.split(':');
        // Pad all parts to 2 digits
        input.value = parts.map(p => p.padStart(2, '0')).join(':');
    }
}

function formatTime(seconds) {
    if (seconds === null || seconds === undefined || isNaN(seconds)) {
        return '--:--';
    }
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
        return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// =====================================================
// TASK MANAGER — tarjetas flotantes para tareas de fondo (descargas / conversiones)
// En vez de un modal que tapa toda la app, cada tarea vive en su propia tarjeta en la esquina;
// se puede seguir navegando, escaneando otro video o subiendo otro archivo mientras corren.
// Máximo MAX_CONCURRENT_TASKS a la vez (para no saturar la conexión ni ffmpeg); el resto espera en cola.
// =====================================================
const MAX_CONCURRENT_TASKS = 3;
let activeTaskCount = 0;
const taskWaitQueue = [];
const taskCancelHandlers = new Map();

function enqueueTask(taskId, runner) {
    if (activeTaskCount < MAX_CONCURRENT_TASKS) {
        activeTaskCount++;
        runner().finally(() => {
            activeTaskCount--;
            const next = taskWaitQueue.shift();
            if (next) enqueueTask(next.taskId, next.runner);
        });
    } else {
        updateTaskCard(taskId, { status: 'En cola — esperando su turno...' });
        taskWaitQueue.push({ taskId, runner });
    }
}

function createTaskCard(taskId, title, iconName) {
    const manager = document.getElementById('taskManager');
    if (!manager) return;
    const card = document.createElement('div');
    card.className = 'task-card';
    card.id = `task-${taskId}`;
    card.innerHTML = `
        <div class="task-card-header">
            <div class="task-card-icon" id="taskIcon-${taskId}"><i data-lucide="${iconName}" style="width: 16px; height: 16px;"></i></div>
            <div class="task-card-info">
                <div class="task-card-title" title="${title}">${title}</div>
                <div class="task-card-status" id="taskStatus-${taskId}">En cola...</div>
            </div>
            <span class="task-card-percent" id="taskPercent-${taskId}"></span>
            <button class="task-card-close" title="Cancelar" onclick="cancelTask('${taskId}')">
                <i data-lucide="x" style="width: 14px; height: 14px;"></i>
            </button>
        </div>
        <div class="progress-bar"><div class="progress-fill" id="taskFill-${taskId}" style="width: 0%"></div></div>
    `;
    manager.appendChild(card);
    lucide.createIcons();
    return card;
}

function updateTaskCard(taskId, { percent, status, done, error } = {}) {
    const fill = document.getElementById(`taskFill-${taskId}`);
    const statusEl = document.getElementById(`taskStatus-${taskId}`);
    const percentEl = document.getElementById(`taskPercent-${taskId}`);
    const iconEl = document.getElementById(`taskIcon-${taskId}`);
    if (!fill) return; // la tarjeta ya se cerró (p. ej. el usuario la canceló)

    if (percent !== undefined) {
        fill.style.width = `${percent}%`;
        if (percentEl) percentEl.textContent = `${Math.round(percent)}%`;
    }
    if (status && statusEl) statusEl.textContent = status;
    if (done && iconEl) {
        iconEl.classList.add('done');
        iconEl.innerHTML = '<i data-lucide="check" style="width: 16px; height: 16px;"></i>';
        lucide.createIcons();
    }
    if (error && iconEl) {
        iconEl.classList.add('error');
        iconEl.innerHTML = '<i data-lucide="alert-circle" style="width: 16px; height: 16px;"></i>';
        lucide.createIcons();
    }
}

function removeTaskCard(taskId, delay = 0) {
    taskCancelHandlers.delete(taskId);
    setTimeout(() => {
        document.getElementById(`task-${taskId}`)?.remove();
    }, delay);
}

function setTaskCancelHandler(taskId, handler) {
    taskCancelHandlers.set(taskId, handler);
}

function cancelTask(taskId) {
    const handler = taskCancelHandlers.get(taskId);
    if (handler) handler();
    else removeTaskCard(taskId); // sin forma de cancelar el trabajo del servidor (p. ej. conversión H.264): solo se oculta la tarjeta
}

async function download() {
    const url = document.getElementById('url').value;
    const startTime = document.getElementById('startTime')?.value;
    const endTime = document.getElementById('endTime')?.value;

    if (!url) {
        showModal('error', 'alert-circle', 'Error', 'Por favor ingresa una URL válida');
        return;
    }

    // Recorte: se puede llenar solo el inicio, solo el fin o los dos.
    const trimStart = parseClock(startTime);
    const trimEnd = parseClock(endTime);
    if ((startTime?.trim() && trimStart === null) || (endTime?.trim() && trimEnd === null)) {
        showModal('error', 'alert-circle', 'Revisa el recorte', 'Escribe los tiempos como minutos:segundos, por ejemplo 01:30.');
        return;
    }
    if (trimEnd !== null && trimEnd <= (trimStart || 0)) {
        showModal('error', 'alert-circle', 'Revisa el recorte', 'El fin tiene que ser mayor que el inicio.');
        return;
    }

    const format = selectedFormat;
    const quality = selectedQuality;
    const audioQuality = selectedAudioQuality;
    const title = document.querySelector('#videoInfo h3')?.textContent?.trim() || `Video (${format.toUpperCase()})`;

    const taskId = 'dl-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
    createTaskCard(taskId, title, format === 'mp3' ? 'music' : 'video');

    // Limpia el formulario de inmediato: la tarea sigue en su tarjeta, y ya se puede escanear otra URL.
    document.getElementById('url').value = '';
    const videoInfo = document.getElementById('videoInfo');
    if (videoInfo) videoInfo.style.display = 'none';

    enqueueTask(taskId, () => runDownloadTask(taskId, { url, format, startTime, endTime, quality, audioQuality }));
}

// ---- Progreso de la descarga en lenguaje llano (antes: «2.42MiB/s · ETA 08:38») ----

function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return '';
    const units = ['KB', 'MB', 'GB'];
    let value = bytes / 1024;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit++; }
    const text = (value >= 100 || unit === 0) ? String(Math.round(value)) : value.toFixed(1).replace('.', ',');
    return `${text} ${units[unit]}`;
}

function formatRemaining(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return '';
    const total = Math.round(seconds);
    if (total < 60) return `${Math.max(total, 1)} s`;
    const minutes = Math.floor(total / 60);
    if (minutes < 60) return (minutes < 10 && total % 60) ? `${minutes} min ${total % 60} s` : `${minutes} min`;
    return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

function formatClock(seconds) {
    const total = Math.max(0, Math.round(seconds));
    const h = Math.floor(total / 3600);
    const mm = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
    const ss = String(total % 60).padStart(2, '0');
    return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

// "01:30" o "1:02:03" (o solo segundos) -> segundos; null si está vacío o no se entiende
function parseClock(text) {
    const value = (text || '').trim();
    if (!value) return null;
    const parts = value.split(':').map(Number);
    if (parts.length > 3 || parts.some((n) => !Number.isFinite(n) || n < 0)) return null;
    return parts.reduce((acc, n) => acc * 60 + n, 0);
}

function describeTrim(trim) {
    if (!trim) return '';
    if (trim.end === null || trim.end === undefined) return `desde ${formatClock(trim.start)}`;
    return `de ${formatClock(trim.start)} a ${formatClock(trim.end)}`;
}

function describeDownload(progress) {
    const trim = describeTrim(progress.trim);
    if (progress.status === 'downloading') {
        // reintentos y avisos que el motor ya manda redactados
        if (typeof progress.speed === 'string' && /reintent|cobalt/i.test(progress.speed)) return progress.speed;
        const done = formatBytes(progress.downloaded_bytes);
        const total = formatBytes(progress.total_bytes);
        const left = formatRemaining(progress.eta_seconds);
        if (!done && trim) return `Descargando solo ${trim}…`;
        const size = (done && total) ? `${done} de ${total}` : done;
        // lo que más importa va primero, por si la tarjeta recorta el texto
        return left ? [`Faltan ${left}`, size].filter(Boolean).join(' · ') : ['Descargando', size].filter(Boolean).join(' · ');
    }
    if (progress.status === 'processing') {
        if (progress.phase === 'Merger') return 'Uniendo video y audio…';
        if (progress.phase === 'ExtractAudio') return 'Convirtiendo a MP3…';
        return 'Preparando el archivo…';
    }
    return trim ? `Descargando solo ${trim}…` : 'Preparando la descarga…';
}

async function runDownloadTask(taskId, { url, format, startTime, endTime, quality, audioQuality }) {
    try {
        updateTaskCard(taskId, { status: 'Preparando la descarga…' });
        const startResponse = await fetch('/api/download/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                format,
                download_id: Math.random().toString(36).substring(7),
                start_time: startTime || null,
                end_time: endTime || null,
                quality: format === 'mp4' ? quality : null,
                audio_quality: format === 'mp3' ? audioQuality : null
            })
        });

        if (!startResponse.ok) {
            const error = await startResponse.json();
            throw new Error(error.detail || 'Error al iniciar descarga');
        }

        const { download_id } = await startResponse.json();
        setTaskCancelHandler(taskId, () => cancelDownloadTask(taskId, download_id));

        let completed = false;
        while (!completed) {
            await new Promise(resolve => setTimeout(resolve, 500));

            const progressResponse = await fetch(`/api/download/progress/${download_id}`);
            const progress = await progressResponse.json();

            if (progress.status === 'cancelled') {
                return; // cancelDownloadTask ya actualizó y cerró la tarjeta
            }

            const percent = Math.round(progress.percent || 0);
            // Un tramo recortado lo baja FFmpeg, que no informa porcentaje: la barra se mueve sola en
            // vez de quedarse en 0 % como si no pasara nada.
            const noPercent = Boolean(progress.trim) && percent === 0
                && (progress.status === 'starting' || progress.status === 'downloading');
            document.getElementById(`task-${taskId}`)?.classList.toggle('indeterminate', noPercent);
            updateTaskCard(taskId, { percent, status: describeDownload(progress) });

            if (progress.status === 'completed') {
                completed = true;

                const fileResponse = await fetch(`/api/download/file/${download_id}`);
                if (!fileResponse.ok) {
                    throw new Error('Error al obtener el archivo');
                }

                const blob = await fileResponse.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;

                const contentDisposition = fileResponse.headers.get('content-disposition');
                let filename = 'video.' + format;
                if (contentDisposition) {
                    // con espacios o tildes el motor manda filename*=utf-8''Nombre%20codificado
                    const encoded = contentDisposition.match(/filename\*=(?:utf-8'')?([^;]+)/i);
                    const plain = contentDisposition.match(/filename="?([^";]+)"?/i);
                    if (encoded && encoded[1]) {
                        try { filename = decodeURIComponent(encoded[1].trim()); } catch (e) { /* se queda el nombre por defecto */ }
                    } else if (plain && plain[1]) {
                        filename = plain[1].trim();
                    }
                }

                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(downloadUrl);
                a.remove();

                document.getElementById(`task-${taskId}`)?.classList.remove('indeterminate');
                updateTaskCard(taskId, { percent: 100, status: 'Listo: elige dónde guardarlo', done: true });
                removeTaskCard(taskId, 4000);
            } else if (progress.status === 'error') {
                throw new Error(progress.error || 'Error durante la descarga');
            }
        }
    } catch (error) {
        document.getElementById(`task-${taskId}`)?.classList.remove('indeterminate');
        updateTaskCard(taskId, { status: error.message, error: true });
        removeTaskCard(taskId, 15000);   // tiempo para leer por qué falló; la X la cierra antes
    }
}

async function cancelDownloadTask(taskId, downloadId) {
    try {
        const response = await fetch(`/api/download/cancel/${downloadId}`, { method: 'POST' });
        const result = await response.json();
        if (result.cancelled) {
            updateTaskCard(taskId, { status: 'Cancelada' });
            removeTaskCard(taskId, 1200);
        }
    } catch (error) {
        console.error('Error al cancelar:', error);
    }
}

function showModal(type, iconName, title, message) {
    const modalOverlay = document.getElementById('modalOverlay');
    const modalContent = document.getElementById('modalContent');
    const iconHtml = `<i data-lucide="${iconName}" style="width: 48px; height: 48px;"></i>`;

    if (type === 'loading') {
        modalContent.innerHTML = `
                <div class="loading-spinner"></div>
            <div class="modal-title">${title}</div>
            <div class="modal-message">${message}</div>
            `;
    } else {
        modalContent.innerHTML = `
                <div class="modal-icon ${type}">${iconHtml}</div>
            <div class="modal-title">${title}</div>
            <div class="modal-message">${message}</div>
            <button class="modal-btn" onclick="closeModal()">Aceptar</button>
            `;
    }

    modalOverlay.classList.add('show');
    lucide.createIcons();
}

function closeModal() {
    const modalOverlay = document.getElementById('modalOverlay');
    modalOverlay.classList.remove('show');
}

// =====================================================
// H.264 CONVERSION FUNCTIONS
// =====================================================

async function uploadAndConvert() {
    if (!selectedVideoFile) return;
    const file = selectedVideoFile;

    const taskId = 'cv-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
    createTaskCard(taskId, file.name, 'repeat');
    resetUploadZone(); // libera el formulario ya: se puede subir otro archivo mientras este convierte

    enqueueTask(taskId, () => runConvertTask(taskId, file));
}

async function runConvertTask(taskId, file) {
    try {
        updateTaskCard(taskId, { status: 'Subiendo video...' });
        const result = await convertOneVideo(file, (progress) => {
            const percent = Math.round(progress.percent || 0);
            const status = progress.message || (progress.status === 'converting' ? `Convirtiendo... ${percent}%` : 'Iniciando conversión...');
            updateTaskCard(taskId, { percent, status });
        });

        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = `/api/convert/download/${result.convertId}`;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        updateTaskCard(taskId, { percent: 100, status: 'Convertido y descargado ✓', done: true });
        removeTaskCard(taskId, 4000);
    } catch (error) {
        updateTaskCard(taskId, { status: error.message, error: true });
        removeTaskCard(taskId, 15000);   // tiempo para leer por qué falló; la X la cierra antes
    }
}

/** Convierte un solo video ya subido — usado tanto por uploadAndConvert (una tarjeta de tarea) como
 * en bucle por uploadAndConvertBatch (un archivo a la vez, para no saturar ffmpeg con varias
 * conversiones en paralelo). */
async function convertOneVideo(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);

    const startResponse = await fetch('/api/upload-convert', { method: 'POST', body: formData });
    if (!startResponse.ok) {
        const error = await startResponse.json();
        throw new Error(error.detail || 'Error en la subida y conversión');
    }
    const { convert_id } = await startResponse.json();

    for (;;) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const progressResponse = await fetch(`/api/convert/progress/${convert_id}`);
        const progress = await progressResponse.json();
        if (onProgress) onProgress(progress);

        if (progress.status === 'completed') {
            return { convertId: convert_id, filename: progress.filename || `${file.name.replace(/\.[^.]+$/, '')}_h264.mp4` };
        }
        if (progress.status === 'error') {
            throw new Error(progress.error || 'Error durante la conversión');
        }
    }
}

async function uploadAndConvertBatch() {
    if (selectedVideoBatch.length === 0) return;

    const btn = document.getElementById('uploadConvertBtn');
    btn.disabled = true;
    const total = selectedVideoBatch.length;
    let okCount = 0;

    for (let i = 0; i < total; i++) {
        const file = selectedVideoBatch[i];
        const status = document.getElementById(`videoBatchStatus${i}`);
        btn.innerText = `Convirtiendo ${i + 1}/${total}...`;
        if (status) { status.textContent = 'Convirtiendo…'; status.className = 'img-batch-status'; }

        try {
            const result = await convertOneVideo(file, (progress) => {
                if (status && progress.status === 'converting' && progress.percent) {
                    status.textContent = `${Math.round(progress.percent)}%`;
                }
            });

            // Dispara la descarga y sigue con el siguiente sin esperar al usuario.
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = `/api/convert/download/${result.convertId}`;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            if (status) { status.textContent = 'Listo'; status.className = 'img-batch-status done'; }
            okCount++;
            // Pequeña pausa entre descargas para que el navegador no las bloquee por venir muy seguidas.
            await new Promise(resolve => setTimeout(resolve, 800));
        } catch (error) {
            if (status) { status.textContent = 'Error'; status.className = 'img-batch-status error'; }
        }
    }

    btn.disabled = false;
    btn.innerText = `Convertir todos (${total})`;
    showModal(
        okCount === total ? 'success' : 'error',
        okCount === total ? 'check-circle-2' : 'alert-circle',
        okCount === total ? '¡Completado!' : 'Terminado con errores',
        `${okCount} de ${total} videos se convirtieron y descargaron correctamente.`
    );
}

// =====================================================
// AUDIO EXTRACTION FUNCTIONS
// =====================================================
let selectedAudioFile = null;
let selectedAudioBatch = [];

function handleAudioFiles(files) {
    if (files.length === 0) return;

    const validExts = ['.mp4', '.mkv', '.avi', '.mov', '.webm'];
    const valid = [];
    for (const file of Array.from(files)) {
        const filename = file.name.toLowerCase();
        if (file.size > 500 * 1024 * 1024) {
            showModal('error', 'alert-circle', 'Error', `${file.name} supera el límite de 500MB`);
            continue;
        }
        if (!validExts.some(ext => filename.endsWith(ext))) {
            showModal('error', 'alert-circle', 'Error', `${file.name}: formato no soportado. Usa MP4, MKV, AVI, MOV o WEBM.`);
            continue;
        }
        valid.push(file);
    }
    if (valid.length === 0) return;

    if (valid.length === 1) {
        handleSingleAudioSelection(valid[0]);
    } else {
        handleAudioBatchSelection(valid);
    }
}

function handleSingleAudioSelection(file) {
    selectedAudioFile = file;
    selectedAudioBatch = [];
    document.getElementById('audioBatchList').style.display = 'none';

    const title = document.getElementById('audioUploadTitle');
    const subtitle = document.getElementById('audioUploadSubtitle');
    const btn = document.getElementById('uploadExtractBtn');

    title.innerHTML = `<i data-lucide="file-video" style="width: 24px; vertical-align: middle;"></i> ${file.name}`;
    subtitle.innerHTML = `${(file.size / (1024 * 1024)).toFixed(1)} MB - Listo para extraer audio`;

    btn.classList.remove('disabled-btn');
    btn.innerText = 'Subir y Extraer Audio (MP3)';
    btn.onclick = uploadAndExtractAudio;

    lucide.createIcons();
}

function handleAudioBatchSelection(files) {
    selectedAudioFile = null;
    selectedAudioBatch = files;

    const title = document.getElementById('audioUploadTitle');
    const subtitle = document.getElementById('audioUploadSubtitle');
    const btn = document.getElementById('uploadExtractBtn');
    const list = document.getElementById('audioBatchList');

    const totalMB = (files.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024)).toFixed(1);
    title.innerHTML = `<i data-lucide="files" style="width: 24px; vertical-align: middle;"></i> ${files.length} videos seleccionados`;
    subtitle.innerHTML = `${totalMB} MB en total - se extraen uno por uno`;

    list.style.display = 'flex';
    list.innerHTML = files.map((file, i) => `
        <li class="file-item" id="audioBatchItem${i}">
            <div class="file-icon"><i data-lucide="file-video" style="width:18px;height:18px;"></i></div>
            <div class="file-info">
                <div class="file-name">${file.name}</div>
                <div class="file-meta"><span>${(file.size / (1024 * 1024)).toFixed(1)} MB</span></div>
            </div>
            <span class="img-batch-status" id="audioBatchStatus${i}">Pendiente</span>
        </li>`).join('');

    btn.classList.remove('disabled-btn');
    btn.innerText = `Extraer audio de todos (${files.length})`;
    btn.onclick = uploadAndExtractAudioBatch;

    lucide.createIcons();
}

function resetAudioUploadZone() {
    selectedAudioFile = null;
    selectedAudioBatch = [];
    const title = document.getElementById('audioUploadTitle');
    const subtitle = document.getElementById('audioUploadSubtitle');
    const btn = document.getElementById('uploadExtractBtn');
    const list = document.getElementById('audioBatchList');

    title.innerHTML = 'Haz clic o arrastra uno o más videos aquí';
    subtitle.innerHTML = 'Formatos soportados: MP4, WEBM, MKV, AVI, MOV (Máx 500MB c/u) · puedes elegir varios a la vez';

    btn.classList.add('disabled-btn');
    btn.innerText = 'Selecciona un archivo primero';
    btn.onclick = uploadAndExtractAudio;
    list.style.display = 'none';
    list.innerHTML = '';
    document.getElementById('audioFileInput').value = '';
}

async function uploadAndExtractAudio() {
    if (!selectedAudioFile) return;
    const file = selectedAudioFile;

    const taskId = 'ea-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
    createTaskCard(taskId, file.name, 'file-audio');
    resetAudioUploadZone(); // libera el formulario ya: se puede subir otro archivo mientras este extrae

    enqueueTask(taskId, () => runExtractAudioTask(taskId, file));
}

async function runExtractAudioTask(taskId, file) {
    try {
        updateTaskCard(taskId, { status: 'Subiendo video...' });
        const result = await extractOneAudio(file, (progress) => {
            const percent = Math.round(progress.percent || 0);
            const status = progress.message || (progress.status === 'converting' ? `Extrayendo... ${percent}%` : 'Iniciando extracción...');
            updateTaskCard(taskId, { percent, status });
        });

        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = `/api/extract-audio/download/${result.extractId}`;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        updateTaskCard(taskId, { percent: 100, status: 'Audio extraído y descargado ✓', done: true });
        removeTaskCard(taskId, 4000);
    } catch (error) {
        updateTaskCard(taskId, { status: error.message, error: true });
        removeTaskCard(taskId, 15000);   // tiempo para leer por qué falló; la X la cierra antes
    }
}

/** Extrae el audio de un solo video ya subido — usado tanto por uploadAndExtractAudio (una tarjeta
 * de tarea) como en bucle por uploadAndExtractAudioBatch (un archivo a la vez). */
async function extractOneAudio(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);

    const startResponse = await fetch('/api/upload-extract-audio', { method: 'POST', body: formData });
    if (!startResponse.ok) {
        const error = await startResponse.json();
        throw new Error(error.detail || 'Error en la subida y extracción');
    }
    const { extract_id } = await startResponse.json();

    for (;;) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const progressResponse = await fetch(`/api/extract-audio/progress/${extract_id}`);
        const progress = await progressResponse.json();
        if (onProgress) onProgress(progress);

        if (progress.status === 'completed') {
            return { extractId: extract_id, filename: progress.filename || `${file.name.replace(/\.[^.]+$/, '')}.mp3` };
        }
        if (progress.status === 'error') {
            throw new Error(progress.error || 'Error durante la extracción');
        }
    }
}

async function uploadAndExtractAudioBatch() {
    if (selectedAudioBatch.length === 0) return;

    const btn = document.getElementById('uploadExtractBtn');
    btn.disabled = true;
    const total = selectedAudioBatch.length;
    let okCount = 0;

    for (let i = 0; i < total; i++) {
        const file = selectedAudioBatch[i];
        const status = document.getElementById(`audioBatchStatus${i}`);
        btn.innerText = `Extrayendo ${i + 1}/${total}...`;
        if (status) { status.textContent = 'Extrayendo…'; status.className = 'img-batch-status'; }

        try {
            const result = await extractOneAudio(file, (progress) => {
                if (status && progress.status === 'converting' && progress.percent) {
                    status.textContent = `${Math.round(progress.percent)}%`;
                }
            });

            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = `/api/extract-audio/download/${result.extractId}`;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            if (status) { status.textContent = 'Listo'; status.className = 'img-batch-status done'; }
            okCount++;
            await new Promise(resolve => setTimeout(resolve, 800));
        } catch (error) {
            if (status) { status.textContent = 'Error'; status.className = 'img-batch-status error'; }
        }
    }

    btn.disabled = false;
    btn.innerText = `Extraer audio de todos (${total})`;
    showModal(
        okCount === total ? 'success' : 'error',
        okCount === total ? 'check-circle-2' : 'alert-circle',
        okCount === total ? '¡Completado!' : 'Terminado con errores',
        `${okCount} de ${total} audios se extrajeron y descargaron correctamente.`
    );
}

// =====================================================
// PDF COMPRESSION
// =====================================================
let selectedPdfFile = null;
let currentPdfCompressId = null;
let pdfCompressMode = 'quality'; // 'quality' | 'size'

const pdfFileInput = document.getElementById('pdfFileInput');
if (pdfFileInput) {
    pdfFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handlePdfSelection(file);
    });
}

const pdfUploadZone = document.getElementById('pdfUploadZone');
if (pdfUploadZone) {
    pdfUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        pdfUploadZone.classList.add('drag-over');
    });

    pdfUploadZone.addEventListener('dragleave', () => {
        pdfUploadZone.classList.remove('drag-over');
    });

    pdfUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        pdfUploadZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && file.name.toLowerCase().endsWith('.pdf')) {
            handlePdfSelection(file);
        }
    });
}

const pdfQualitySlider = document.getElementById('pdfQualitySlider');
if (pdfQualitySlider) {
    pdfQualitySlider.addEventListener('input', updatePdfQualityHint);
}

document.querySelectorAll('.pdf-mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.pdf-mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        pdfCompressMode = btn.getAttribute('data-pdfmode');

        const qualityGroup = document.getElementById('pdfQualityGroup');
        const sizeGroup = document.getElementById('pdfSizeGroup');
        if (qualityGroup) qualityGroup.style.display = pdfCompressMode === 'quality' ? 'block' : 'none';
        if (sizeGroup) sizeGroup.style.display = pdfCompressMode === 'size' ? 'block' : 'none';
    });
});

function updatePdfQualityHint() {
    const slider = document.getElementById('pdfQualitySlider');
    const val = document.getElementById('pdfQualityValue');
    const hint = document.getElementById('pdfQualityHint');
    if (!slider) return;

    const q = parseInt(slider.value);
    if (val) val.textContent = q;
    if (hint) {
        if (q >= 100) hint.textContent = 'Solo optimización de estructura, sin tocar las imágenes.';
        else if (q >= 85) hint.textContent = 'Recompresión ligera, calidad casi idéntica a la original.';
        else if (q >= 60) hint.textContent = 'Buen equilibrio entre calidad y peso final.';
        else hint.textContent = 'Compresión agresiva, prioriza reducir el peso.';
    }
}

function handlePdfSelection(file) {
    selectedPdfFile = file;

    const uploadZone = document.getElementById('pdfUploadZone');
    const panel = document.getElementById('pdfPanel');
    const resetBtn = document.getElementById('pdfResetBtn');
    if (uploadZone) uploadZone.style.display = 'none';
    if (panel) panel.style.display = 'block';
    if (resetBtn) resetBtn.style.display = 'inline-flex';

    const info = document.getElementById('pdfFileInfo');
    if (info) {
        const sizeMB = (file.size / 1024 / 1024).toFixed(1);
        info.textContent = `${file.name} · ${sizeMB} MB`;
    }

    updatePdfQualityHint();
    lucide.createIcons();
}

function resetPdfCompress() {
    selectedPdfFile = null;
    currentPdfCompressId = null;

    const uploadZone = document.getElementById('pdfUploadZone');
    const panel = document.getElementById('pdfPanel');
    const resetBtn = document.getElementById('pdfResetBtn');
    if (uploadZone) uploadZone.style.display = 'block';
    if (panel) panel.style.display = 'none';
    if (resetBtn) resetBtn.style.display = 'none';

    const fileInput = document.getElementById('pdfFileInput');
    if (fileInput) fileInput.value = '';

    const slider = document.getElementById('pdfQualitySlider');
    if (slider) slider.value = 80;
    updatePdfQualityHint();

    pdfCompressMode = 'quality';
    document.querySelectorAll('.pdf-mode-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-pdfmode') === 'quality');
    });
    const qualityGroup = document.getElementById('pdfQualityGroup');
    const sizeGroup = document.getElementById('pdfSizeGroup');
    if (qualityGroup) qualityGroup.style.display = 'block';
    if (sizeGroup) sizeGroup.style.display = 'none';
}

async function compressPdf() {
    if (!selectedPdfFile) return;

    const btn = document.getElementById('pdfCompressBtn');
    if (btn) btn.disabled = true;

    const quality = document.getElementById('pdfQualitySlider')?.value || 80;
    const maxSizeMB = document.getElementById('pdfMaxSizeMB')?.value || 30;
    const originalSize = selectedPdfFile.size;

    if (pdfCompressMode === 'size' && (!maxSizeMB || maxSizeMB <= 0)) {
        showModal('error', 'x-circle', 'Error', 'Ingresa un peso máximo válido en MB.');
        if (btn) btn.disabled = false;
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedPdfFile);
    if (pdfCompressMode === 'size') {
        formData.append('max_size_mb', maxSizeMB);
    } else {
        formData.append('quality', quality);
    }

    try {
        showPdfProgressModal();

        const startResponse = await fetch('/api/pdf/compress', {
            method: 'POST',
            body: formData
        });

        if (!startResponse.ok) {
            const error = await startResponse.json();
            throw new Error(error.detail || 'Error al iniciar la compresión');
        }

        const { compress_id } = await startResponse.json();
        currentPdfCompressId = compress_id;

        let completed = false;
        while (!completed) {
            await new Promise(resolve => setTimeout(resolve, 800));

            const progressResponse = await fetch(`/api/pdf/compress/progress/${compress_id}`);
            const progress = await progressResponse.json();

            updatePdfProgressModal(progress);

            if (progress.status === 'completed') {
                completed = true;
                currentPdfCompressId = null;

                closeModal();

                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = `/api/pdf/compress/download/${compress_id}`;
                a.download = `${selectedPdfFile.name.replace(/\.pdf$/i, '')}_comprimido.pdf`;
                document.body.appendChild(a);
                a.click();

                const finalSize = progress.final_size || originalSize;
                const savings = Math.max(0, Math.round((1 - finalSize / originalSize) * 100));
                const origMB = (originalSize / 1024 / 1024).toFixed(1);
                const finalMB = (finalSize / 1024 / 1024).toFixed(1);

                let message = `${origMB} MB → ${finalMB} MB (-${savings}%). La descarga comenzó automáticamente.`;
                let modalType = 'success';
                let modalTitle = '¡PDF comprimido!';

                if (pdfCompressMode === 'size') {
                    if (progress.reached_target === false) {
                        modalType = 'error';
                        modalTitle = 'No se pudo alcanzar el peso máximo';
                        message = `Ni con la compresión más agresiva se logró bajar de ${maxSizeMB} MB. ` +
                            `Mejor resultado posible: ${origMB} MB → ${finalMB} MB (-${savings}%). Se descargó igual.`;
                    } else {
                        message = `${origMB} MB → ${finalMB} MB, dentro del límite de ${maxSizeMB} MB ` +
                            `(calidad ${progress.quality_used}%). La descarga comenzó automáticamente.`;
                    }
                }

                setTimeout(() => {
                    document.body.removeChild(a);
                    showModal(modalType, modalType === 'success' ? 'check-circle-2' : 'alert-triangle', modalTitle, message);
                    resetPdfCompress();
                }, 800);

            } else if (progress.status === 'error') {
                throw new Error(progress.error || 'Error durante la compresión');
            }
        }
    } catch (error) {
        closeModal();
        showModal('error', 'x-circle', 'Error', error.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function showPdfProgressModal() {
    const modalOverlay = document.getElementById('modalOverlay');
    const modalContent = document.getElementById('modalContent');

    modalContent.innerHTML = `
        <div class="modal-icon" style="color: #000000;">
            <i data-lucide="file-archive" style="width: 48px; height: 48px;"></i>
        </div>
        <div class="modal-title">Comprimiendo PDF...</div>
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="pdfProgressFill" style="width: 0%"></div>
            </div>
            <div class="progress-info">
                <span id="pdfProgressPercent">0%</span>
            </div>
            <div class="progress-details" id="pdfProgressDetails">Subiendo archivo...</div>
        </div>
    `;

    modalOverlay.classList.add('show');
    lucide.createIcons();
}

function updatePdfProgressModal(progress) {
    const progressFill = document.getElementById('pdfProgressFill');
    const progressPercent = document.getElementById('pdfProgressPercent');
    const progressDetails = document.getElementById('pdfProgressDetails');

    if (!progressFill) return;

    const percent = Math.round(progress.percent || 0);
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;

    if (progress.message) {
        progressDetails.textContent = progress.message;
    }
}

// =====================================================
// IMAGE FORMAT CONVERSION
// =====================================================
let selectedImageFile = null;
let selectedImgFormat = 'webp';
let imgAspectRatio = 1;
let imgAspectLocked = true;
let imgOriginalWidth = 0;
let imgOriginalHeight = 0;
let previewDebounceTimer = null;

// Conversión por lotes (varias imágenes a la vez)
let selectedBatchFiles = [];
let selectedBatchFormat = 'webp';

// Recibe la lista de archivos elegida (input o drop) y decide si es una imagen (editor de
// una sola, con vista previa y redimensionar) o varias (lista simple + mismo formato para todas).
function handleImageFilesPicked(fileList) {
    const files = Array.from(fileList).filter(f => f.type.startsWith('image/') || /\.(png|jpe?g|webp|avif|bmp|tiff?)$/i.test(f.name));
    if (files.length === 0) return;
    if (files.length === 1) {
        handleImageSelection(files[0]);
    } else {
        handleBatchSelection(files);
    }
}

// Image file input handler
const imageFileInput = document.getElementById('imageFileInput');
if (imageFileInput) {
    imageFileInput.addEventListener('change', (e) => {
        handleImageFilesPicked(e.target.files);
    });
}

// Drag and drop for image upload zone
const imgUploadZone = document.getElementById('imgUploadZone');
if (imgUploadZone) {
    imgUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        imgUploadZone.classList.add('drag-over');
    });

    imgUploadZone.addEventListener('dragleave', () => {
        imgUploadZone.classList.remove('drag-over');
    });

    imgUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        imgUploadZone.classList.remove('drag-over');
        handleImageFilesPicked(e.dataTransfer.files);
    });
}

// Formato para el modo por lotes
document.querySelectorAll('.imgb-format-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.imgb-format-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedBatchFormat = btn.getAttribute('data-imgformat');
        const qualityGroup = document.getElementById('imgBatchQualityGroup');
        if (qualityGroup) qualityGroup.style.display = selectedBatchFormat === 'png' ? 'none' : 'block';
        updateBatchConvertBtnText();
    });
});

const imgBatchQualitySlider = document.getElementById('imgBatchQualitySlider');
if (imgBatchQualitySlider) {
    imgBatchQualitySlider.addEventListener('input', () => {
        const val = document.getElementById('imgBatchQualityValue');
        if (val) val.textContent = imgBatchQualitySlider.value;
    });
}

function updateBatchConvertBtnText() {
    const btn = document.getElementById('imgBatchConvertBtn');
    if (btn) btn.textContent = `Convertir todas (${selectedBatchFiles.length}) a ${selectedBatchFormat.toUpperCase()}`;
}

function handleBatchSelection(files) {
    selectedBatchFiles = files;

    const uploadZone = document.getElementById('imgUploadZone');
    const editorPanel = document.getElementById('imgEditorPanel');
    const batchPanel = document.getElementById('imgBatchPanel');
    if (uploadZone) uploadZone.style.display = 'none';
    if (editorPanel) editorPanel.style.display = 'none';
    if (batchPanel) batchPanel.style.display = 'block';

    const resetBtn = document.getElementById('imgResetBtn');
    if (resetBtn) resetBtn.style.display = 'inline-flex';

    renderBatchList();
    updateBatchConvertBtnText();
    lucide.createIcons();
}

function renderBatchList() {
    const list = document.getElementById('imgBatchList');
    if (!list) return;
    list.innerHTML = selectedBatchFiles.map((file, i) => {
        const sizeKB = (file.size / 1024).toFixed(1);
        const ext = file.name.split('.').pop().toUpperCase();
        return `
            <li class="file-item" id="imgBatchItem${i}">
                <div class="file-icon"><i data-lucide="image" style="width:18px;height:18px;"></i></div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta"><span>${ext}</span><span>${sizeKB}KB</span></div>
                </div>
                <span class="img-batch-status" id="imgBatchStatus${i}">Pendiente</span>
            </li>`;
    }).join('');
    lucide.createIcons();
}

async function convertImagesBatch() {
    if (selectedBatchFiles.length === 0) return;

    const convertBtn = document.getElementById('imgBatchConvertBtn');
    const originalText = convertBtn.textContent;
    convertBtn.textContent = 'Convirtiendo...';
    convertBtn.classList.add('disabled-btn');
    selectedBatchFiles.forEach((_, i) => {
        const status = document.getElementById(`imgBatchStatus${i}`);
        if (status) { status.textContent = 'Convirtiendo…'; status.className = 'img-batch-status'; }
    });

    const quality = document.getElementById('imgBatchQualitySlider')?.value || 85;
    const formData = new FormData();
    selectedBatchFiles.forEach(file => formData.append('files', file));

    try {
        const response = await fetch(`/api/convert-images-batch?target_format=${selectedBatchFormat}&quality=${quality}`, {
            method: 'POST', body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error de conversión');
        }

        // Todas se pidieron a la vez (un solo request), así que si la respuesta llegó bien
        // se marcan todas como completadas — los errores individuales van dentro del zip.
        selectedBatchFiles.forEach((_, i) => {
            const status = document.getElementById(`imgBatchStatus${i}`);
            if (status) { status.textContent = 'Listo'; status.className = 'img-batch-status done'; }
        });

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'imagenes_convertidas.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        convertBtn.textContent = `Descargado (${selectedBatchFiles.length} imágenes)`;
        convertBtn.classList.remove('disabled-btn');
        setTimeout(() => { convertBtn.textContent = originalText; }, 4000);

    } catch (error) {
        selectedBatchFiles.forEach((_, i) => {
            const status = document.getElementById(`imgBatchStatus${i}`);
            if (status) { status.textContent = 'Error'; status.className = 'img-batch-status error'; }
        });
        showModal('error', 'x-circle', 'Error', error.message);
        convertBtn.textContent = originalText;
        convertBtn.classList.remove('disabled-btn');
    }
}

// Image format buttons
document.querySelectorAll('.img-format-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.img-format-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedImgFormat = btn.getAttribute('data-imgformat');

        // Show/hide quality slider (PNG is lossless)
        const qualityGroup = document.getElementById('imgQualityGroup');
        if (qualityGroup) {
            qualityGroup.style.display = selectedImgFormat === 'png' ? 'none' : 'block';
        }

        // Update button text
        updateImgConvertBtnText();

        // Trigger preview
        schedulePreview();
    });
});

// Quality slider
const imgQualitySlider = document.getElementById('imgQualitySlider');
if (imgQualitySlider) {
    imgQualitySlider.addEventListener('input', () => {
        const val = document.getElementById('imgQualityValue');
        if (val) val.textContent = imgQualitySlider.value;
        schedulePreview();
    });
}

// Resize inputs
const imgWidthInput = document.getElementById('imgWidth');
const imgHeightInput = document.getElementById('imgHeight');

if (imgWidthInput) {
    imgWidthInput.addEventListener('input', () => {
        if (imgAspectLocked && imgWidthInput.value) {
            const w = parseInt(imgWidthInput.value);
            imgHeightInput.value = Math.round(w / imgAspectRatio);
        }
        schedulePreview();
    });
}

if (imgHeightInput) {
    imgHeightInput.addEventListener('input', () => {
        if (imgAspectLocked && imgHeightInput.value) {
            const h = parseInt(imgHeightInput.value);
            imgWidthInput.value = Math.round(h * imgAspectRatio);
        }
        schedulePreview();
    });
}

function toggleAspectLock() {
    imgAspectLocked = !imgAspectLocked;
    const btn = document.getElementById('imgAspectLock');
    if (btn) {
        btn.classList.toggle('active', imgAspectLocked);
        btn.innerHTML = imgAspectLocked
            ? '<i data-lucide="lock" style="width: 14px; height: 14px;"></i>'
            : '<i data-lucide="unlock" style="width: 14px; height: 14px;"></i>';
        lucide.createIcons();
    }
}

function updateImgConvertBtnText() {
    const convertBtn = document.getElementById('imgConvertBtn');
    if (convertBtn && selectedImageFile) {
        convertBtn.textContent = `Convertir a ${selectedImgFormat.toUpperCase()}`;
    }
}

function handleImageSelection(file) {
    selectedImageFile = file;

    // Hide upload zone, show editor panel and reset button
    const uploadZone = document.getElementById('imgUploadZone');
    const editorPanel = document.getElementById('imgEditorPanel');
    const resetBtn = document.getElementById('imgResetBtn');
    if (uploadZone) uploadZone.style.display = 'none';
    if (editorPanel) editorPanel.style.display = 'block';
    if (resetBtn) resetBtn.style.display = 'inline-flex';

    // Show original preview
    const previewImg = document.getElementById('imgPreviewOriginal');
    if (previewImg) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;

            // Get natural dimensions after load
            const tmpImg = new Image();
            tmpImg.onload = () => {
                imgOriginalWidth = tmpImg.naturalWidth;
                imgOriginalHeight = tmpImg.naturalHeight;
                imgAspectRatio = imgOriginalWidth / imgOriginalHeight;

                // Set dimension inputs
                const wInput = document.getElementById('imgWidth');
                const hInput = document.getElementById('imgHeight');
                if (wInput) wInput.value = imgOriginalWidth;
                if (hInput) hInput.value = imgOriginalHeight;

                // Show original info
                const origInfo = document.getElementById('imgOriginalInfo');
                const ext = file.name.split('.').pop().toUpperCase();
                const sizeKB = (file.size / 1024).toFixed(1);
                if (origInfo) origInfo.textContent = `${ext} · ${imgOriginalWidth}×${imgOriginalHeight} · ${sizeKB}KB`;
            };
            tmpImg.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    // Auto-select best format
    const inputExt = file.name.split('.').pop().toLowerCase();
    const extMap = { 'jpg': 'jpg', 'jpeg': 'jpg', 'png': 'png', 'webp': 'webp', 'avif': 'avif' };
    const inputFormat = extMap[inputExt] || inputExt;
    const preferenceOrder = ['webp', 'jpg', 'png', 'avif'];
    const bestFormat = preferenceOrder.find(f => f !== inputFormat) || 'webp';

    document.querySelectorAll('.img-format-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-imgformat') === bestFormat);
    });
    selectedImgFormat = bestFormat;

    // Show/hide quality for PNG
    const qualityGroup = document.getElementById('imgQualityGroup');
    if (qualityGroup) qualityGroup.style.display = selectedImgFormat === 'png' ? 'none' : 'block';

    updateImgConvertBtnText();
    lucide.createIcons();
}

function resetImageConverter() {
    selectedImageFile = null;
    imgOriginalWidth = 0;
    imgOriginalHeight = 0;
    selectedBatchFiles = [];

    // Show upload zone, hide editor/batch panels and reset button
    const uploadZone = document.getElementById('imgUploadZone');
    const editorPanel = document.getElementById('imgEditorPanel');
    const batchPanel = document.getElementById('imgBatchPanel');
    const resetBtn = document.getElementById('imgResetBtn');
    if (uploadZone) uploadZone.style.display = 'block';
    if (editorPanel) editorPanel.style.display = 'none';
    if (batchPanel) batchPanel.style.display = 'none';
    if (resetBtn) resetBtn.style.display = 'none';

    const batchList = document.getElementById('imgBatchList');
    if (batchList) batchList.innerHTML = '';

    // Reset upload zone text
    const title = document.getElementById('imgUploadTitle');
    const subtitle = document.getElementById('imgUploadSubtitle');
    if (title) title.textContent = 'Haz clic o arrastra una o más imágenes aquí';
    if (subtitle) subtitle.textContent = 'Formatos: PNG, JPG, WebP, AVIF, BMP, TIFF · puedes elegir varias a la vez';

    // Clear images
    const origImg = document.getElementById('imgPreviewOriginal');
    const resultImg = document.getElementById('imgPreviewResult');
    const placeholder = document.getElementById('imgResultPlaceholder');
    if (origImg) origImg.src = '';
    if (resultImg) { resultImg.src = ''; resultImg.style.display = 'none'; }
    if (placeholder) placeholder.style.display = 'flex';

    // Clear info badges
    const origInfo = document.getElementById('imgOriginalInfo');
    const resultInfo = document.getElementById('imgResultInfo');
    if (origInfo) origInfo.textContent = '';
    if (resultInfo) resultInfo.textContent = '';

    // Reset inputs
    const wInput = document.getElementById('imgWidth');
    const hInput = document.getElementById('imgHeight');
    if (wInput) wInput.value = '';
    if (hInput) hInput.value = '';

    // Reset file input
    const fileInput = document.getElementById('imageFileInput');
    if (fileInput) fileInput.value = '';

    // Reset quality
    const slider = document.getElementById('imgQualitySlider');
    const qVal = document.getElementById('imgQualityValue');
    if (slider) slider.value = 85;
    if (qVal) qVal.textContent = '85';

    lucide.createIcons();
}

function schedulePreview() {
    if (!selectedImageFile) return;
    clearTimeout(previewDebounceTimer);
    previewDebounceTimer = setTimeout(() => generatePreview(), 500);
}

async function generatePreview() {
    if (!selectedImageFile) return;

    const resultImg = document.getElementById('imgPreviewResult');
    const placeholder = document.getElementById('imgResultPlaceholder');
    const resultInfo = document.getElementById('imgResultInfo');

    const quality = document.getElementById('imgQualitySlider')?.value || 85;
    const width = document.getElementById('imgWidth')?.value || '';
    const height = document.getElementById('imgHeight')?.value || '';

    let queryParams = `target_format=${selectedImgFormat}&quality=${quality}`;
    if (width) queryParams += `&width=${width}`;
    if (height) queryParams += `&height=${height}`;

    const formData = new FormData();
    formData.append('file', selectedImageFile);

    try {
        const response = await fetch(`/api/convert-image?${queryParams}`, {
            method: 'POST', body: formData
        });

        if (!response.ok) return;

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        if (resultImg) {
            resultImg.src = url;
            resultImg.style.display = 'block';
        }
        if (placeholder) placeholder.style.display = 'none';

        // Show result info
        const sizeKB = (blob.size / 1024).toFixed(1);
        const savings = ((1 - blob.size / selectedImageFile.size) * 100).toFixed(0);
        const dimText = (width && height) ? `${width}×${height} · ` : '';
        const savingsText = savings > 0 ? `(-${savings}%)` : `(+${Math.abs(savings)}%)`;
        if (resultInfo) resultInfo.textContent = `${selectedImgFormat.toUpperCase()} · ${dimText}${sizeKB}KB ${savingsText}`;

    } catch (err) {
        // Silent fail for preview
    }
}

function uploadWithProgress(url, formData, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        xhr.responseType = 'blob';

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                // La subida es solo una parte del trabajo: el resto (0-100 de esta fase)
                // se completa mientras el servidor procesa la imagen, sin datos que subir.
                onProgress(Math.round((e.loaded / e.total) * 100), 'uploading');
            }
        };
        xhr.upload.onload = () => onProgress(100, 'processing');

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(xhr.response);
                return;
            }
            const reader = new FileReader();
            reader.onload = () => {
                let message = 'Error de conversión';
                try { message = JSON.parse(reader.result).detail || message; } catch { /* noop */ }
                reject(new Error(message));
            };
            reader.onerror = () => reject(new Error('Error de conversión'));
            reader.readAsText(xhr.response);
        };
        xhr.onerror = () => reject(new Error('Error de red'));
        xhr.send(formData);
    });
}

async function convertImage() {
    if (!selectedImageFile) return;

    const convertBtn = document.getElementById('imgConvertBtn');
    const originalText = convertBtn.textContent;
    convertBtn.classList.add('disabled-btn');

    const quality = document.getElementById('imgQualitySlider')?.value || 85;
    const width = document.getElementById('imgWidth')?.value || '';
    const height = document.getElementById('imgHeight')?.value || '';

    let queryParams = `target_format=${selectedImgFormat}&quality=${quality}`;
    if (width) queryParams += `&width=${width}`;
    if (height) queryParams += `&height=${height}`;

    const formData = new FormData();
    formData.append('file', selectedImageFile);

    // El servidor no reporta avance de la conversión en sí (es una sola respuesta HTTP),
    // así que tras terminar la subida simulamos un avance suave hasta 95% para que el
    // usuario nunca vea un texto estático sin señal de cuánto falta.
    let processingTimer = null;
    const startProcessingAnimation = () => {
        let fake = 0;
        convertBtn.textContent = 'Procesando... 0%';
        processingTimer = setInterval(() => {
            fake = Math.min(fake + Math.random() * 8, 95);
            convertBtn.textContent = `Procesando... ${Math.round(fake)}%`;
        }, 200);
    };
    const stopProcessingAnimation = () => {
        if (processingTimer) { clearInterval(processingTimer); processingTimer = null; }
    };

    try {
        const blob = await uploadWithProgress(`/api/convert-image?${queryParams}`, formData, (percent, phase) => {
            if (phase === 'uploading') {
                convertBtn.textContent = `Subiendo... ${percent}%`;
            } else if (phase === 'processing' && !processingTimer) {
                startProcessingAnimation();
            }
        });
        stopProcessingAnimation();

        const originalName = selectedImageFile.name.replace(/\.[^.]+$/, '');
        const fileName = `${originalName}.${selectedImgFormat}`;

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        const originalSize = (selectedImageFile.size / 1024).toFixed(1);
        const convertedSize = (blob.size / 1024).toFixed(1);
        convertBtn.textContent = `Descargado (${originalSize}KB → ${convertedSize}KB)`;
        convertBtn.classList.remove('disabled-btn');

        setTimeout(() => { convertBtn.textContent = originalText; }, 4000);

    } catch (error) {
        stopProcessingAnimation();
        showModal('error', 'x-circle', 'Error', error.message);
        convertBtn.textContent = originalText;
        convertBtn.classList.remove('disabled-btn');
    }
}


// =====================================================
// OUTPAINTING (AI IMAGE EXPANSION)
// =====================================================
let opSelectedFile = null;
let opDirection = 'all';
let opGpuChecked = false;

// Check GPU status when page loads
async function checkGpuStatus() {
    const badge = document.getElementById('opGpuBadge');
    const text = document.getElementById('opGpuText');
    if (!badge || !text) return;

    try {
        const response = await fetch('/api/outpaint/status');
        const data = await response.json();

        if (data.status === 'ok' && data.gpu?.available) {
            badge.className = 'op-gpu-badge ready';
            text.textContent = `${data.gpu.name} (${data.gpu.vram_total}GB)`;
            if (data.gpu.model_loaded) {
                text.textContent += ' · Modelo cargado';
            }
        } else {
            badge.className = 'op-gpu-badge error';
            text.textContent = data.message || 'GPU no disponible';
        }
    } catch (e) {
        badge.className = 'op-gpu-badge error';
        text.textContent = 'Error verificando GPU';
    }
    opGpuChecked = true;
}

// Run check on first view access
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        if (item.getAttribute('data-view') === 'outpaintView' && !opGpuChecked) {
            checkGpuStatus();
        }
    });
});

// File input
const opFileInput = document.getElementById('opFileInput');
if (opFileInput) {
    opFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleOpFileSelection(file);
    });
}

// Drag and drop
const opUploadZone = document.getElementById('opUploadZone');
if (opUploadZone) {
    opUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        opUploadZone.classList.add('drag-over');
    });
    opUploadZone.addEventListener('dragleave', () => {
        opUploadZone.classList.remove('drag-over');
    });
    opUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        opUploadZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) handleOpFileSelection(file);
    });
}

// Direction buttons
document.querySelectorAll('.op-dir-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.op-dir-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        opDirection = btn.getAttribute('data-dir');
    });
});

// Sliders
const opPixelsSlider = document.getElementById('opPixelsSlider');
if (opPixelsSlider) {
    opPixelsSlider.addEventListener('input', () => {
        document.getElementById('opPixelsValue').textContent = opPixelsSlider.value;
    });
}

const opStepsSlider = document.getElementById('opStepsSlider');
if (opStepsSlider) {
    opStepsSlider.addEventListener('input', () => {
        document.getElementById('opStepsValue').textContent = opStepsSlider.value;
    });
}

function handleOpFileSelection(file) {
    opSelectedFile = file;

    document.getElementById('opUploadZone').style.display = 'none';
    document.getElementById('opEditorPanel').style.display = 'block';
    document.getElementById('opResetBtn').style.display = 'inline-flex';

    const previewImg = document.getElementById('opPreviewOriginal');
    if (previewImg) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;

            const tmpImg = new Image();
            tmpImg.onload = () => {
                const origInfo = document.getElementById('opOriginalInfo');
                const ext = file.name.split('.').pop().toUpperCase();
                const sizeKB = (file.size / 1024).toFixed(1);
                if (origInfo) origInfo.textContent = `${ext} · ${tmpImg.naturalWidth}×${tmpImg.naturalHeight} · ${sizeKB}KB`;
            };
            tmpImg.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    lucide.createIcons();
}

function resetOutpaint() {
    opSelectedFile = null;

    document.getElementById('opUploadZone').style.display = 'block';
    document.getElementById('opEditorPanel').style.display = 'none';
    document.getElementById('opResetBtn').style.display = 'none';

    const origImg = document.getElementById('opPreviewOriginal');
    const resultImg = document.getElementById('opPreviewResult');
    const placeholder = document.getElementById('opResultPlaceholder');
    if (origImg) origImg.src = '';
    if (resultImg) { resultImg.src = ''; resultImg.style.display = 'none'; }
    if (placeholder) placeholder.style.display = 'flex';

    document.getElementById('opOriginalInfo').textContent = '';
    document.getElementById('opResultInfo').textContent = '';
    document.getElementById('opFileInput').value = '';

    lucide.createIcons();
}

async function runOutpaint() {
    if (!opSelectedFile) return;

    const expandBtn = document.getElementById('opExpandBtn');
    const originalHTML = expandBtn.innerHTML;
    expandBtn.innerHTML = '<i data-lucide="loader" style="width: 18px;" class="spin"></i> Generando con IA...';
    expandBtn.classList.add('disabled-btn');
    lucide.createIcons();

    const pixels = document.getElementById('opPixelsSlider')?.value || 128;
    const steps = document.getElementById('opStepsSlider')?.value || 20;
    const prompt = document.getElementById('opPrompt')?.value || '';

    const formData = new FormData();
    formData.append('file', opSelectedFile);

    let queryParams = `direction=${opDirection}&pixels=${pixels}&steps=${steps}`;
    if (prompt) queryParams += `&prompt=${encodeURIComponent(prompt)}`;

    try {
        const response = await fetch(`/api/outpaint?${queryParams}`, {
            method: 'POST', body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error en outpainting');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        // Show result
        const resultImg = document.getElementById('opPreviewResult');
        const placeholder = document.getElementById('opResultPlaceholder');
        if (resultImg) { resultImg.src = url; resultImg.style.display = 'block'; }
        if (placeholder) placeholder.style.display = 'none';

        // Result info
        const resultInfo = document.getElementById('opResultInfo');
        const sizeKB = (blob.size / 1024).toFixed(1);
        if (resultInfo) resultInfo.textContent = `PNG · ${sizeKB}KB`;

        // Enable download on click
        resultImg.style.cursor = 'pointer';
        resultImg.onclick = () => {
            const a = document.createElement('a');
            a.href = url;
            a.download = `${opSelectedFile.name.replace(/\.[^.]+$/, '')}_outpainted.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };

        expandBtn.innerHTML = originalHTML;
        expandBtn.classList.remove('disabled-btn');

    } catch (error) {
        showModal('error', 'x-circle', 'Error', error.message);
        expandBtn.innerHTML = originalHTML;
        expandBtn.classList.remove('disabled-btn');
    }
    lucide.createIcons();
}

// ==========================================================
// REMBG LOGIC
// ==========================================================
let rbSelectedFile = null;

function handleRembgFileSelection(file) {
    rbSelectedFile = file;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('rbPreviewOriginal').src = e.target.result;
        document.getElementById('rbUploadZone').style.display = 'none';
        document.getElementById('rbEditorPanel').style.display = 'block';
        document.getElementById('rbResetBtn').style.display = 'flex';
        
        // Set info
        const img = new Image();
        img.onload = function() {
            const kb = (rbSelectedFile.size / 1024).toFixed(1);
            document.getElementById('rbOriginalInfo').textContent = `${img.width}x${img.height} - ${kb}KB`;
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(rbSelectedFile);
}

const rbFileInput = document.getElementById('rbFileInput');
if (rbFileInput) {
    rbFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleRembgFileSelection(e.target.files[0]);
        }
    });
}

// Interactividad para las configuraciones avanzadas de rembg
const rbAlphaMatting = document.getElementById('rbAlphaMatting');
const rbAlphaMattingOptions = document.getElementById('rbAlphaMattingOptions');
if (rbAlphaMatting && rbAlphaMattingOptions) {
    rbAlphaMatting.addEventListener('change', () => {
        rbAlphaMattingOptions.style.display = rbAlphaMatting.checked ? 'block' : 'none';
    });
}

const rbErodeSlider = document.getElementById('rbErodeSlider');
const rbErodeValue = document.getElementById('rbErodeValue');
if (rbErodeSlider && rbErodeValue) {
    rbErodeSlider.addEventListener('input', () => {
        rbErodeValue.textContent = rbErodeSlider.value;
    });
}

const rbBgThresholdSlider = document.getElementById('rbBgThresholdSlider');
const rbBgThresholdValue = document.getElementById('rbBgThresholdValue');
if (rbBgThresholdSlider && rbBgThresholdValue) {
    rbBgThresholdSlider.addEventListener('input', () => {
        rbBgThresholdValue.textContent = rbBgThresholdSlider.value;
    });
}

const rbFgThresholdSlider = document.getElementById('rbFgThresholdSlider');
const rbFgThresholdValue = document.getElementById('rbFgThresholdValue');
if (rbFgThresholdSlider && rbFgThresholdValue) {
    rbFgThresholdSlider.addEventListener('input', () => {
        rbFgThresholdValue.textContent = rbFgThresholdSlider.value;
    });
}

// Drag and drop for rembg upload zone
const rbUploadZone = document.getElementById('rbUploadZone');
if (rbUploadZone) {
    rbUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        rbUploadZone.classList.add('drag-over');
    });

    rbUploadZone.addEventListener('dragleave', () => {
        rbUploadZone.classList.remove('drag-over');
    });

    rbUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        rbUploadZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            handleRembgFileSelection(file);
        }
    });
}

function resetRembg() {
    rbSelectedFile = null;
    if(rbFileInput) rbFileInput.value = '';
    
    document.getElementById('rbPreviewOriginal').src = '';
    document.getElementById('rbPreviewResult').src = '';
    document.getElementById('rbPreviewResult').style.display = 'none';
    
    document.getElementById('rbEditorPanel').style.display = 'none';
    document.getElementById('rbUploadZone').style.display = 'block';
    document.getElementById('rbResetBtn').style.display = 'none';
    document.getElementById('rbResultInfo').style.display = 'none';
    
    // Restablecer ajustes avanzados a valores por defecto
    const modelSelect = document.getElementById('rbModelSelect');
    if (modelSelect) modelSelect.value = 'birefnet-portrait';
    
    const alphaMatting = document.getElementById('rbAlphaMatting');
    if (alphaMatting) alphaMatting.checked = true;
    
    const postProcess = document.getElementById('rbPostProcess');
    if (postProcess) postProcess.checked = false;

    const decontaminate = document.getElementById('rbDecontaminate');
    if (decontaminate) decontaminate.checked = false;
    
    const erodeSlider = document.getElementById('rbErodeSlider');
    if (erodeSlider) erodeSlider.value = 5;
    
    const erodeValue = document.getElementById('rbErodeValue');
    if (erodeValue) erodeValue.textContent = '5';
    
    const bgThresholdSlider = document.getElementById('rbBgThresholdSlider');
    if (bgThresholdSlider) bgThresholdSlider.value = 10;
    
    const bgThresholdValue = document.getElementById('rbBgThresholdValue');
    if (bgThresholdValue) bgThresholdValue.textContent = '10';

    const fgThresholdSlider = document.getElementById('rbFgThresholdSlider');
    if (fgThresholdSlider) fgThresholdSlider.value = 240;
    
    const fgThresholdValue = document.getElementById('rbFgThresholdValue');
    if (fgThresholdValue) fgThresholdValue.textContent = '240';
    
    const alphaMattingOptions = document.getElementById('rbAlphaMattingOptions');
    if (alphaMattingOptions) alphaMattingOptions.style.display = 'block';
    
    const btn = document.getElementById('rbProcessBtn');
    if (btn) {
        btn.innerHTML = `<i data-lucide="scissors" style="width: 18px;"></i> Quitar Fondo`;
        btn.classList.remove('disabled-btn');
        btn.onclick = runRembg;
    }
    lucide.createIcons();
}

async function runRembg() {
    if (!rbSelectedFile) return;

    const btn = document.getElementById('rbProcessBtn');
    const originalBtn = btn.innerHTML;
    
    btn.innerHTML = `<div class="op-spinner"></div> Procesando IA...`;
    btn.classList.add('disabled-btn');
    btn.onclick = null;
    
    const model = document.getElementById('rbModelSelect')?.value || 'u2net';
    const alphaMatting = document.getElementById('rbAlphaMatting')?.checked || false;
    const erodeSize = document.getElementById('rbErodeSlider')?.value || 10;
    const fgThreshold = document.getElementById('rbFgThresholdSlider')?.value || 240;
    const bgThreshold = document.getElementById('rbBgThresholdSlider')?.value || 10;
    const postProcess = document.getElementById('rbPostProcess')?.checked || false;
    const decontaminate = document.getElementById('rbDecontaminate')?.checked || false;

    // Configurar cargador con texto dinámico
    const loaderTextElement = document.getElementById('rbLoaderText');
    if (loaderTextElement) {
        if (model !== 'u2net') {
            loaderTextElement.textContent = "Quitando fondo... La primera vez puede tardar 1-2 minutos mientras descarga el modelo seleccionado.";
        } else {
            loaderTextElement.textContent = "Quitando fondo, por favor espera...";
        }
    }
    
    document.getElementById('rbLoader').style.display = 'flex';
    document.getElementById('rbPreviewResult').style.display = 'none';
    document.getElementById('rbResultInfo').style.display = 'none';

    const formData = new FormData();
    formData.append('file', rbSelectedFile);
    formData.append('model', model);
    formData.append('alpha_matting', alphaMatting);
    formData.append('erode_size', erodeSize);
    formData.append('fg_threshold', fgThreshold);
    formData.append('bg_threshold', bgThreshold);
    formData.append('post_process', postProcess);
    formData.append('decontaminate', decontaminate);

    try {
        const response = await fetch('/api/remove-background', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            let errorMsg = 'Fallo al procesar imagen';
            try {
                const err = await response.json();
                errorMsg = err.detail || errorMsg;
            } catch (e) {
                errorMsg = await response.text();
            }
            throw new Error(errorMsg);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        document.getElementById('rbLoader').style.display = 'none';
        
        const preview = document.getElementById('rbPreviewResult');
        preview.src = url;
        preview.style.display = 'block';
        
        const info = document.getElementById('rbResultInfo');
        info.textContent = `PNG Transparente - ${(blob.size / 1024).toFixed(1)}KB`;
        info.style.display = 'inline-block';
        
        // Transform button into download button
        btn.innerHTML = `<i data-lucide="download" style="width: 18px;"></i> Guardar Resultado`;
        btn.classList.remove('disabled-btn');
        
        const originalName = rbSelectedFile.name.replace(/\.[^/.]+$/, "");
        
        btn.onclick = () => {
            const a = document.createElement('a');
            a.href = url;
            a.download = `${originalName}_nobg.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };

    } catch (error) {
        showModal('error', 'x-circle', 'Error', error.message);
        document.getElementById('rbLoader').style.display = 'none';
        btn.innerHTML = originalBtn;
        btn.classList.remove('disabled-btn');
        btn.onclick = runRembg;
    }
    lucide.createIcons();
}


// =====================================================
// APP DE ESCRITORIO: ESTADO, VERSIÓN Y ACTUALIZACIONES
// =====================================================

const appInfo = window.APP_INFO || {};
let updateDismissed = false;
let updatePolling = false;

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
    return String(text ?? '').replace(/[&<>"]/g, (c) => map[c]);
}

// La pastilla de la barra superior: «Listo» o «Trabajando…» mientras haya un diálogo con progreso.
function setStatus(kind, text) {
    const pill = document.getElementById('statusPill');
    const label = document.getElementById('statusText');
    if (!pill || !label) return;
    pill.className = `pill ${kind}`;
    label.textContent = text;
}

(function watchWork() {
    const overlay = document.getElementById('modalOverlay');
    const tasks = document.getElementById('taskManager');
    const refresh = () => {
        // un diálogo con progreso (comprimir PDF) o tarjetas de tareas que aún no terminan
        const inModal = overlay && overlay.classList.contains('show') && overlay.querySelector('.progress-container, .loading-spinner');
        const running = tasks ? tasks.querySelectorAll('.task-card-icon:not(.done):not(.error)').length : 0;
        const working = Boolean(inModal) || running > 0;
        const label = running > 1 ? `${running} tareas en curso` : 'Trabajando…';
        setStatus(working ? 'busy' : 'ready', working ? label : 'Listo');
    };
    const options = { attributes: true, attributeFilter: ['class'], childList: true, subtree: true };
    if (overlay) new MutationObserver(refresh).observe(overlay, options);
    if (tasks) new MutationObserver(refresh).observe(tasks, options);
})();

function renderVersion(state) {
    const label = document.getElementById('versionLabel');
    const link = document.getElementById('updateLink');
    if (!label || !link) return;
    const current = state?.current || appInfo.version || '';
    link.classList.toggle('has-update', Boolean(state?.available));
    label.textContent = state?.available ? `Actualizar a la ${state.version}` : `Versión ${current}`;
    link.title = state?.available ? `Tienes la ${current}` : 'Buscar actualizaciones';
}

function renderUpdateBanner(state) {
    const banners = document.getElementById('banners');
    if (!banners) return;
    banners.querySelector('.banner.update')?.remove();
    if (!state?.available || (updateDismissed && state.status === 'idle')) return;

    const banner = document.createElement('div');
    banner.className = 'banner update';
    const version = escapeHtml(state.version);
    const percent = state.percent || 0;
    if (state.status === 'downloading' || state.status === 'installing') {
        const text = state.status === 'installing'
            ? 'Instalando la actualización: la app se cerrará y volverá a abrirse sola…'
            : `Descargando la versión ${version}… ${percent}%`;
        banner.innerHTML = `<i data-lucide="download"></i><span>${text}</span>`
            + `<div class="banner-bar"><i style="width: ${percent}%"></i></div>`;
    } else if (state.status === 'error') {
        banner.innerHTML = `<i data-lucide="alert-triangle"></i>`
            + `<span>No se pudo actualizar: ${escapeHtml(state.error)}</span>`
            + `<button class="btn sm primary" type="button" data-act="install">Reintentar</button>`
            + `<button class="btn sm ghost" type="button" data-act="page">Descargar a mano</button>`;
    } else {
        const main = state.can_install
            ? `<button class="btn sm primary" type="button" data-act="install">Actualizar ahora</button>`
              + `<button class="btn sm ghost" type="button" data-act="page">Ver cambios</button>`
            : `<button class="btn sm primary" type="button" data-act="page">Ver la descarga</button>`;
        banner.innerHTML = `<i data-lucide="sparkles"></i>`
            + `<span>Hay una versión nueva: <b>${version}</b> (tienes la ${escapeHtml(state.current)}).</span>`
            + main
            + `<button class="icon-btn sm" type="button" data-act="dismiss" title="Ahora no"><i data-lucide="x"></i></button>`;
    }
    banner.addEventListener('click', (e) => {
        const act = e.target.closest('[data-act]')?.dataset.act;
        if (act === 'install') installUpdate();
        if (act === 'page' && state.page) window.open(state.page, '_blank');
        if (act === 'dismiss') { updateDismissed = true; banner.remove(); }
    });
    banners.prepend(banner);
    lucide.createIcons();
}

async function checkForUpdates(manual = false) {
    const link = document.getElementById('updateLink');
    link?.classList.add('checking');
    try {
        const response = await fetch(`/api/update/check${manual ? '?force=true' : ''}`);
        const state = await response.json();
        if (manual) updateDismissed = false;
        renderVersion(state);
        renderUpdateBanner(state);
        if (manual && !state.available) {
            showModal('success', 'check-circle-2', 'Estás al día', `Tienes la versión más reciente (${state.current}).`);
        }
        if (state.status === 'downloading' || state.status === 'installing') pollUpdate();
    } catch (error) {
        if (manual) showModal('error', 'wifi-off', 'Sin conexión', 'No se pudo consultar si hay una versión nueva.');
    } finally {
        link?.classList.remove('checking');
    }
}

async function installUpdate() {
    try {
        const response = await fetch('/api/update/install', { method: 'POST' });
        const state = await response.json();
        if (!response.ok) throw new Error(state.detail || 'No se pudo iniciar la actualización');
        renderUpdateBanner(state);
        pollUpdate();
    } catch (error) {
        showModal('error', 'x-circle', 'No se pudo actualizar', error.message);
    }
}

async function pollUpdate() {
    if (updatePolling) return;
    updatePolling = true;
    try {
        while (true) {
            await new Promise((resolve) => setTimeout(resolve, 600));
            const state = await (await fetch('/api/update/progress')).json();
            renderUpdateBanner(state);
            if (state.status !== 'downloading' && state.status !== 'installing') break;
        }
    } catch (error) {
        // el motor ya se cerró para dejarse reemplazar: el instalador reabre la app
    } finally {
        updatePolling = false;
    }
}

renderVersion(null);
// al abrir (sin molestar si no hay red) y luego cada 6 h si la app queda abierta
setTimeout(() => checkForUpdates(false), 2500);
setInterval(() => checkForUpdates(false), 6 * 3600 * 1000);
