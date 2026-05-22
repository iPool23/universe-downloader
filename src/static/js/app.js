/**
 * YouTube Downloader - Client Side Application
 * 
 * @author Pool Anthony Deza Millones
 * @github @iPool23
 * @version 2.2.0
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
const allViews = ['downloaderView', 'imageConverterView', 'converterView', 'outpaintView', 'rembgView'];

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();

        const targetView = item.getAttribute('data-view');
        if (!targetView) return;

        // Visual Active State
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

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

// Initialize after page load
document.addEventListener('DOMContentLoaded', () => {
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
});

function handleFiles(files) {
    if (files.length === 0) return;
    const file = files[0];

    // Validate size (500MB max)
    if (file.size > 500 * 1024 * 1024) {
        showModal('error', 'alert-circle', 'Error', 'El archivo supera el límite de 500MB');
        return;
    }

    // Validate type
    const validExts = ['.mp4', '.mkv', '.avi', '.mov', '.webm'];
    const filename = file.name.toLowerCase();
    if (!validExts.some(ext => filename.endsWith(ext))) {
        showModal('error', 'alert-circle', 'Error', 'Formato no soportado. Usa MP4, MKV, AVI, MOV o WEBM.');
        return;
    }

    selectedVideoFile = file;

    // Update UI
    const title = document.getElementById('uploadTitle');
    const subtitle = document.getElementById('uploadSubtitle');
    const btn = document.getElementById('uploadConvertBtn');

    title.innerHTML = `<i data-lucide="file-video" style="width: 24px; vertical-align: middle;"></i> ${file.name}`;
    subtitle.innerHTML = `${(file.size / (1024 * 1024)).toFixed(1)} MB - Listo para convertir`;

    btn.classList.remove('disabled-btn');
    btn.innerText = 'Subir y Convertir a H.264';

    lucide.createIcons();
}

function resetUploadZone() {
    selectedVideoFile = null;
    const title = document.getElementById('uploadTitle');
    const subtitle = document.getElementById('uploadSubtitle');
    const btn = document.getElementById('uploadConvertBtn');

    title.innerHTML = 'Haz clic o arrastra un archivo aquí';
    subtitle.innerHTML = 'Formatos soportados: MP4, WEBM, MKV, AVI, MOV (Máx 500MB)';

    btn.classList.add('disabled-btn');
    btn.innerText = 'Selecciona un archivo primero';
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

async function uploadAndConvert() {
    if (!selectedVideoFile) return;

    const btn = document.getElementById('uploadConvertBtn');
    btn.disabled = true;

    const formData = new FormData();
    formData.append('file', selectedVideoFile);

    try {
        showConvertProgressModal();
        document.getElementById('convertProgressDetails').textContent = 'Subiendo video (esto puede tardar unos momentos)...';

        // Use proper fetch for FormData (no Content-Type set manually)
        const startResponse = await fetch('/api/upload-convert', {
            method: 'POST',
            body: formData
        });

        if (!startResponse.ok) {
            const error = await startResponse.json();
            throw new Error(error.detail || 'Error en la subida y conversión');
        }

        const { convert_id } = await startResponse.json();
        currentConvertId = convert_id;

        // Polling para obtener progreso
        let completed = false;
        while (!completed) {
            await new Promise(resolve => setTimeout(resolve, 1000));

            const progressResponse = await fetch(`/api/convert/progress/${convert_id}`);
            const progress = await progressResponse.json();

            updateConvertProgressModal(progress);

            if (progress.status === 'completed') {
                completed = true;
                currentConvertId = null;

                // Download the file
                closeModal();
                showModal('loading', 'loader', 'Descargando...', 'Tu archivo H.264 está listo. Descargando automáticamente...');

                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = `/api/convert/download/${convert_id}`;
                a.download = progress.filename || 'convertido_h264.mp4';
                document.body.appendChild(a);
                a.click();

                setTimeout(() => {
                    document.body.removeChild(a);
                    closeModal();
                    showModal('success', 'check-circle-2', '¡Completado!', 'Tu video ha sido convertido y descargado.');
                    resetUploadZone();
                }, 2000);

            } else if (progress.status === 'error') {
                throw new Error(progress.error || 'Error durante la conversión');
            }
        }
    } catch (error) {
        closeModal();
        showModal('error', 'x-circle', 'Error', error.message);
    } finally {
        if (btn) btn.disabled = false;
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

// Image file input handler
const imageFileInput = document.getElementById('imageFileInput');
if (imageFileInput) {
    imageFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleImageSelection(file);
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
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            handleImageSelection(file);
        }
    });
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

    // Show upload zone, hide editor panel and reset button
    const uploadZone = document.getElementById('imgUploadZone');
    const editorPanel = document.getElementById('imgEditorPanel');
    const resetBtn = document.getElementById('imgResetBtn');
    if (uploadZone) uploadZone.style.display = 'block';
    if (editorPanel) editorPanel.style.display = 'none';
    if (resetBtn) resetBtn.style.display = 'none';

    // Reset upload zone text
    const title = document.getElementById('imgUploadTitle');
    const subtitle = document.getElementById('imgUploadSubtitle');
    if (title) title.textContent = 'Haz clic o arrastra una imagen aquí';
    if (subtitle) subtitle.textContent = 'Formatos: PNG, JPG, WebP, AVIF, BMP, TIFF';

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

async function convertImage() {
    if (!selectedImageFile) return;

    const convertBtn = document.getElementById('imgConvertBtn');
    const originalText = convertBtn.textContent;
    convertBtn.textContent = 'Convirtiendo...';
    convertBtn.classList.add('disabled-btn');

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

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error de conversión');
        }

        const blob = await response.blob();
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
        alert(`Error: ${error.message}`);
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
        alert(`Error: ${error.message}`);
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
        alert(`Error: ${error.message}`);
        document.getElementById('rbLoader').style.display = 'none';
        btn.innerHTML = originalBtn;
        btn.classList.remove('disabled-btn');
        btn.onclick = runRembg;
    }
    lucide.createIcons();
}
