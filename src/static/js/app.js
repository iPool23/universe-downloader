/**
 * YouTube Downloader - Client Side Application
 * 
 * @author Pool Anthony Deza Millones
 * @github @iPool23
 * @version 1.0.0
 */

let selectedFormat = 'mp4';

// Manejo de botones de formato
document.querySelectorAll('.format-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        selectedFormat = this.dataset.format;
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
        const files = await response.json();

        if (files.length === 0) {
            list.innerHTML = '<div style="text-align:center; padding: 40px; color: #888;">No hay descargas recientes</div>';
            return;
        }

        list.innerHTML = files.map(file => {
            const icon = file.type === 'video' ? 'film' : 'music';
            const escapedPath = file.path.replace(/\\/g, '\\\\'); // Escape backslashes for JS string

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
                        <button class="action-btn play" title="Reproducir" onclick="playMedia('${file.filename}', '${file.type}')">
                            <i data-lucide="play" style="width: 16px;"></i>
                        </button>
                        <button class="action-btn" title="Abrir Ubicación" onclick="openFolder('${escapedPath}')">
                            <i data-lucide="folder" style="width: 16px;"></i>
                        </button>
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
    scanBtn.innerHTML = '<i data-lucide="loader-2" class="spin-anim" style="width: 18px;"></i> Escaneando...';
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

        videoInfo.innerHTML = `
                <div class="video-details">
                <div class="thumb-container">
                    <img src="${data.thumbnail}" class="video-thumb" alt="Thumbnail">
                </div>
                <div class="video-meta">
                    <h3 title="${data.title}">${data.title}</h3>
                    <p><i data-lucide="clock" style="width: 14px;"></i> ${formattedDuration}</p>
                </div>
            </div >
                <div class="time-range-container">
                    <span class="time-range-label"><i data-lucide="scissors" style="width: 14px;"></i> Recortar (Opcional):</span>
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
        scanBtn.innerHTML = '<i data-lucide="search" style="width: 18px;"></i> Escanear';
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

    showModal('loading', '', 'Descargando...', 'Por favor espera mientras se descarga el archivo');
    downloadBtn.disabled = true;

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                format: selectedFormat,
                download_id: Math.random().toString(36).substring(7),
                start_time: startTime || null,
                end_time: endTime || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al descargar');
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;

        const contentDisposition = response.headers.get('content-disposition');
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
    } catch (error) {
        showModal('error', 'x-circle', 'Error', error.message);
    } finally {
        downloadBtn.disabled = false;
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
