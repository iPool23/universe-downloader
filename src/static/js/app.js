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
    btn.addEventListener('click', function() {
        document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        selectedFormat = this.dataset.format;
    });
});

async function download() {
    const url = document.getElementById('url').value;
    const downloadBtn = document.querySelector('.download-btn');
    
    if (!url) {
        showModal('error', '⚠️', 'Error', 'Por favor ingresa una URL válida');
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
                download_id: Math.random().toString(36).substring(7)
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
        
        showModal('success', '✅', '¡Descarga Completada!', 'El archivo se ha guardado correctamente');
    } catch (error) {
        showModal('error', '❌', 'Error', error.message);
    } finally {
        downloadBtn.disabled = false;
    }
}

function showModal(type, icon, title, message) {
    const modalOverlay = document.getElementById('modalOverlay');
    const modalContent = document.getElementById('modalContent');
    
    if (type === 'loading') {
        modalContent.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="modal-title">${title}</div>
            <div class="modal-message">${message}</div>
        `;
    } else {
        modalContent.innerHTML = `
            <div class="modal-icon">${icon}</div>
            <div class="modal-title">${title}</div>
            <div class="modal-message">${message}</div>
            <button class="modal-btn" onclick="closeModal()">Aceptar</button>
        `;
    }
    
    modalOverlay.classList.add('show');
}

function closeModal() {
    const modalOverlay = document.getElementById('modalOverlay');
    modalOverlay.classList.remove('show');
}
