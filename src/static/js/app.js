/**
 * YouTube Downloader - Client Side Application
 * 
 * @author Pool Anthony Deza Millones
 * @github @iPool23
 * @version 2.1.0
 */

let selectedFormat = 'mp4';
let selectedQuality = null;
let selectedAudioQuality = 192; // Por defecto 192kbps
let availableQualities = [];
let currentDownloadId = null; // ID de la descarga actual para poder cancelarla

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
const navItems = document.querySelectorAll('.nav-item');

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();

        // Simple text check
        const text = item.innerText;
        const isDownloads = text.indexOf('Descargas') !== -1;
        const isHome = text.indexOf('Inicio') !== -1;

        if (!isDownloads && !isHome) return;

        // Visual Active State
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

        // View Switching
        const downloaderView = document.getElementById('downloaderView');
        const downloadsView = document.getElementById('downloadsView');

        // Hide all first
        if (downloaderView) downloaderView.style.display = 'none';
        if (downloadsView) downloadsView.style.display = 'none';

        if (isHome) {
            if (downloaderView) downloaderView.style.display = 'block';
        } else if (isDownloads) {
            if (downloadsView) downloadsView.style.display = 'block';
            loadDownloads();
        }
    });
});

async function loadDownloads() {
    const list = document.getElementById('downloadsList');
    list.innerHTML = '<div class="loading-spinner" style="margin: 20px auto;"></div>';

    try {
        const response = await fetch('/api/downloads');
        let files = await response.json();

        // Filtrar archivos .part (descargas incompletas)
        files = files.filter(file => !file.filename.endsWith('.part'));

        if (files.length === 0) {
            list.innerHTML = '<div style="text-align:center; padding: 40px; color: #888;">No hay descargas recientes</div>';
            return;
        }

        list.innerHTML = files.map(file => {
            const escapedPath = file.path.replace(/\\/g, '\\\\');
            const isMedia = file.type === 'video' || file.type === 'audio';

            // Determinar ícono
            let icon = 'file';
            if (file.type === 'video') icon = 'film';
            else if (file.type === 'audio') icon = 'music';

            // Construir botones según el tipo de archivo
            let actionsHtml = '';

            if (isMedia) {
                // Botón de conversión a H.264 solo para videos
                const convertBtn = file.type === 'video' && !file.filename.includes('_h264')
                    ? `<button class="action-btn" title="Convertir a H.264" onclick="convertToH264('${file.filename}')">
                           <i data-lucide="repeat" style="width: 16px;"></i>
                       </button>`
                    : '';

                actionsHtml = `
                    <button class="action-btn play" title="Reproducir" onclick="playMedia('${file.filename}', '${file.type}')">
                        <i data-lucide="play" style="width: 16px;"></i>
                    </button>
                    ${convertBtn}
                    <button class="action-btn" title="Abrir Ubicación" onclick="openFolder('${escapedPath}')">
                        <i data-lucide="folder" style="width: 16px;"></i>
                    </button>
                `;
            } else {
                // Otro tipo de archivo: solo carpeta
                actionsHtml = `
                    <button class="action-btn" title="Abrir Ubicación" onclick="openFolder('${escapedPath}')">
                        <i data-lucide="folder" style="width: 16px;"></i>
                    </button>
                `;
            }

            return `
                <div class="file-item">
                    <div class="file-icon">
                        <i data-lucide="${icon}"></i>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${file.filename}</div>
                        <div class="file-meta">
                            <span>${file.size}</span>
                            <span>•</span>
                            <span>${file.created_at}</span>
                        </div>
                    </div>
                    <div class="file-actions">
                        ${actionsHtml}
                    </div>
                </div>
            `;
        }).join('');
        lucide.createIcons();
    } catch (error) {
        list.innerHTML = '<div style="color: red; text-align: center;">Error al cargar descargas</div>';
    }
}

function playMedia(filename, type) {
    const modal = document.getElementById('mediaPlayerModal');
    const content = document.getElementById('playerContent');
    const title = document.getElementById('playerTitle');

    title.textContent = filename;

    // Prevent caching issues by adding timestamp
    const src = `/content/${encodeURIComponent(filename)}?t=${new Date().getTime()}`;

    if (type === 'video') {
        content.innerHTML = `<video controls autoplay src="${src}"></video>`;
    } else {
        content.innerHTML = `
                <div style="padding: 40px; text-align: center; width: 100%;">
                <i data-lucide="music" style="width: 64px; height: 64px; color: #4403E8; margin-bottom: 20px;"></i>
                <audio controls autoplay src="${src}" style="width: 100%;"></audio>
            </div >
                `;
        lucide.createIcons();
    }

    modal.classList.add('show');
}

function closePlayer() {
    const modal = document.getElementById('mediaPlayerModal');
    const content = document.getElementById('playerContent');
    content.innerHTML = ''; // Stop playback
    modal.classList.remove('show');
}

async function openFolder(path) {
    try {
        await fetch('/api/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        });
    } catch (error) {
        console.error('Error opening folder:', error);
    }
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
    scanBtn.innerHTML = '<i data-lucide="search" style="width: 18px; color: white"></i> Escaneando...';
    videoInfo.style.display = 'none';

    try {
        const response = await fetch(`/api/scan?url=${encodeURIComponent(url)}`);
        if (!response.ok) throw new Error('No se pudo obtener la información del video');

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
                    <span class="time-range-label"><i data-lucide="scissors" style="width: 14px; margin-bottom: -6px;"></i> Recortar (Opcional):</span>
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
                </div>
            `;
        videoInfo.style.display = 'block';
        lucide.createIcons();

    } catch (error) {
        showModal('error', 'x-circle', 'Error', error.message);
    } finally {
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<i data-lucide="search" style="width: 18px; color: white"></i> Escanear';
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

async function download() {
    const url = document.getElementById('url').value;
    const downloadBtn = document.querySelector('.download-btn');
    const startTime = document.getElementById('startTime')?.value;
    const endTime = document.getElementById('endTime')?.value;

    if (!url) {
        showModal('error', 'alert-circle', 'Error', 'Por favor ingresa una URL válida');
        return;
    }

    showProgressModal();
    downloadBtn.disabled = true;

    try {
        // Iniciar descarga en segundo plano
        const startResponse = await fetch('/api/download/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                format: selectedFormat,
                download_id: Math.random().toString(36).substring(7),
                start_time: startTime || null,
                end_time: endTime || null,
                quality: selectedFormat === 'mp4' ? selectedQuality : null,
                audio_quality: selectedFormat === 'mp3' ? selectedAudioQuality : null
            })
        });

        if (!startResponse.ok) {
            const error = await startResponse.json();
            throw new Error(error.detail || 'Error al iniciar descarga');
        }

        const { download_id } = await startResponse.json();
        currentDownloadId = download_id; // Guardar para poder cancelar

        // Polling para obtener progreso
        let completed = false;
        while (!completed) {
            await new Promise(resolve => setTimeout(resolve, 500)); // Esperar 500ms

            const progressResponse = await fetch(`/api/download/progress/${download_id}`);
            const progress = await progressResponse.json();

            // Si fue cancelada, salir del loop
            if (progress.status === 'cancelled') {
                completed = true;
                currentDownloadId = null;
                return; // El modal de cancelación ya se mostró
            }

            updateProgressModal(progress);

            if (progress.status === 'completed') {
                completed = true;
                currentDownloadId = null;

                // Descargar el archivo
                const fileResponse = await fetch(`/api/download/file/${download_id}`);
                if (!fileResponse.ok) {
                    throw new Error('Error al obtener el archivo');
                }

                const blob = await fileResponse.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;

                const contentDisposition = fileResponse.headers.get('content-disposition');
                let filename = 'video.' + selectedFormat;
                if (contentDisposition) {
                    const matches = contentDisposition.match(/filename="?(.+)"?/);
                    if (matches && matches[1]) {
                        filename = matches[1].replace(/"/g, '');
                    }
                }

                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(downloadUrl);
                a.remove();

                showModal('success', 'check-circle-2', '¡Descarga Completada!', 'El archivo se ha guardado correctamente');
            } else if (progress.status === 'error') {
                throw new Error(progress.error || 'Error durante la descarga');
            }
        }
    } catch (error) {
        showModal('error', 'x-circle', 'Error', error.message);
    } finally {
        downloadBtn.disabled = false;
    }
}

function showProgressModal() {
    const modalOverlay = document.getElementById('modalOverlay');
    const modalContent = document.getElementById('modalContent');

    modalContent.innerHTML = `
        <div class="modal-title">Descargando...</div>
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
            <div class="progress-info">
                <span id="progressPercent">0%</span>
                <span id="progressSpeed"></span>
            </div>
            <div class="progress-details" id="progressDetails">Iniciando descarga...</div>
        </div>
        <button class="modal-btn cancel-btn" onclick="cancelDownload()">
            <i data-lucide="x" style="width: 16px; height: 16px;"></i> Cancelar Descarga
        </button>
    `;

    modalOverlay.classList.add('show');
    lucide.createIcons();
}

async function cancelDownload() {
    if (!currentDownloadId) return;

    try {
        const response = await fetch(`/api/download/cancel/${currentDownloadId}`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.cancelled) {
            closeModal();
            showModal('error', 'x-circle', 'Descarga Cancelada', 'La descarga ha sido cancelada');
        }
    } catch (error) {
        console.error('Error al cancelar:', error);
    }
}

function updateProgressModal(progress) {
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressSpeed = document.getElementById('progressSpeed');
    const progressDetails = document.getElementById('progressDetails');

    if (!progressFill) return;

    const percent = Math.round(progress.percent || 0);
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;

    if (progress.speed) {
        progressSpeed.textContent = progress.speed;
    }

    if (progress.status === 'downloading') {
        const downloaded = progress.downloaded || '';
        const total = progress.total || '';
        const eta = progress.eta ? `ETA: ${progress.eta}` : '';
        progressDetails.textContent = `${downloaded} / ${total} ${eta}`.trim();
    } else if (progress.status === 'processing') {
        progressDetails.textContent = 'Procesando video...';
    } else if (progress.status === 'starting') {
        progressDetails.textContent = 'Iniciando descarga...';
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

let currentConvertId = null;

async function convertToH264(filename) {
    showConvertProgressModal();

    try {
        // Iniciar conversión en segundo plano
        const startResponse = await fetch('/api/convert', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ filename: filename })
        });

        if (!startResponse.ok) {
            const error = await startResponse.json();
            throw new Error(error.detail || 'Error al iniciar conversión');
        }

        const { convert_id } = await startResponse.json();
        currentConvertId = convert_id;

        // Polling para obtener progreso
        let completed = false;
        while (!completed) {
            await new Promise(resolve => setTimeout(resolve, 1000)); // Esperar 1s

            const progressResponse = await fetch(`/api/convert/progress/${convert_id}`);
            const progress = await progressResponse.json();

            updateConvertProgressModal(progress);

            if (progress.status === 'completed') {
                completed = true;
                currentConvertId = null;

                showModal('success', 'check-circle-2', '¡Conversión Completada!', 'El archivo H.264 se ha creado correctamente');

                // Recargar lista de descargas para mostrar el nuevo archivo
                loadDownloads();

            } else if (progress.status === 'error') {
                throw new Error(progress.error || 'Error durante la conversión');
            }
        }
    } catch (error) {
        showModal('error', 'x-circle', 'Error', error.message);
    }
}

function showConvertProgressModal() {
    const modalOverlay = document.getElementById('modalOverlay');
    const modalContent = document.getElementById('modalContent');

    modalContent.innerHTML = `
        <div class="modal-icon" style="color: #000000;">
            <i data-lucide="repeat" style="width: 48px; height: 48px;"></i>
        </div>
        <div class="modal-title">Convirtiendo a H.264...</div>
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="convertProgressFill" style="width: 0%"></div>
            </div>
            <div class="progress-info">
                <span id="convertProgressPercent">0%</span>
            </div>
            <div class="progress-details" id="convertProgressDetails">Iniciando conversión...</div>
        </div>
    `;

    modalOverlay.classList.add('show');
    lucide.createIcons();
}

function updateConvertProgressModal(progress) {
    const progressFill = document.getElementById('convertProgressFill');
    const progressPercent = document.getElementById('convertProgressPercent');
    const progressDetails = document.getElementById('convertProgressDetails');

    if (!progressFill) return;

    const percent = Math.round(progress.percent || 0);
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent}%`;

    if (progress.message) {
        progressDetails.textContent = progress.message;
    } else if (progress.status === 'converting') {
        progressDetails.textContent = 'Convirtiendo video a H.264...';
    } else if (progress.status === 'starting') {
        progressDetails.textContent = 'Iniciando conversión...';
    }
}
