// ================================================
// MSG to EML Converter - Modern Frontend JavaScript
// Email Transformation Hub - 2025
// ================================================

// ================================================
// Global State
// ================================================
let selectedFiles = [];
let convertedFiles = [];

// ================================================
// DOM Elements
// ================================================
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const filesContainer = document.getElementById('files-container');
const convertBtn = document.getElementById('convert-btn');
const fileCountSpan = document.getElementById('file-count');
const progressArea = document.getElementById('progress-area');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const progressMessage = document.getElementById('progress-message');
const resultsArea = document.getElementById('results-area');
const resultsMessage = document.getElementById('results-message');
const downloadButtons = document.getElementById('download-buttons');
const errorsArea = document.getElementById('errors-area');
const errorsList = document.getElementById('errors-list');
const resetArea = document.getElementById('reset-area');
const uploadStatus = document.getElementById('upload-status');

// ================================================
// Initialize Application
// ================================================
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    initializeAccessibility();
});

// ================================================
// Event Listeners Setup
// ================================================
function setupEventListeners() {
    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Upload area interactions
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Keyboard accessibility for upload zone
    uploadArea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
        }
    });

    // Prevent default drag behavior on window
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.body.addEventListener(eventName, preventDefaults, false);
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// ================================================
// Accessibility Initialization
// ================================================
function initializeAccessibility() {
    // Set initial ARIA attributes
    updateAriaLive('Aplicación lista para usar');
}

function updateAriaLive(message) {
    if (uploadStatus) {
        uploadStatus.textContent = message;
    }
}

// ================================================
// File Selection Handler
// ================================================
function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFiles(files);
}

// ================================================
// Drag & Drop Handlers with Visual Feedback
// ================================================
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.add('dragover');
    updateAriaLive('Archivo sobre la zona de carga');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();

    // Only remove dragover if we're actually leaving the upload area
    const rect = uploadArea.getBoundingClientRect();
    if (
        e.clientX < rect.left ||
        e.clientX >= rect.right ||
        e.clientY < rect.top ||
        e.clientY >= rect.bottom
    ) {
        uploadArea.classList.remove('dragover');
    }
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');

    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
}

// ================================================
// Add Files with Validation
// ================================================
function addFiles(files) {
    // Filter MSG files only
    const msgFiles = files.filter(file => file.name.toLowerCase().endsWith('.msg'));
    const invalidFiles = files.filter(file => !file.name.toLowerCase().endsWith('.msg'));

    // Show error for invalid files with shake animation
    if (invalidFiles.length > 0 && msgFiles.length === 0) {
        showError('Por favor selecciona archivos MSG válidos');
        uploadArea.classList.add('shake');
        setTimeout(() => uploadArea.classList.remove('shake'), 500);
        updateAriaLive('Error: Solo se permiten archivos MSG');
        return;
    }

    if (msgFiles.length === 0) {
        return;
    }

    // Add valid files
    selectedFiles = [...selectedFiles, ...msgFiles];
    displayFileList();

    // Show file list with animation
    fileList.style.display = 'block';
    fileList.classList.add('fade-in');

    // Update accessibility announcement
    updateAriaLive(`${msgFiles.length} archivo${msgFiles.length > 1 ? 's' : ''} agregado${msgFiles.length > 1 ? 's' : ''}. Total: ${selectedFiles.length}`);

    // Notify about invalid files if any
    if (invalidFiles.length > 0) {
        setTimeout(() => {
            showError(`${invalidFiles.length} archivo${invalidFiles.length > 1 ? 's' : ''} no MSG ${invalidFiles.length > 1 ? 'fueron ignorados' : 'fue ignorado'}`);
        }, 100);
    }
}

// ================================================
// Display File List with Modern Cards
// ================================================
function displayFileList() {
    filesContainer.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item slide-in-up';
        fileItem.setAttribute('role', 'listitem');

        // File info container
        const fileInfo = document.createElement('div');
        fileInfo.className = 'file-icon-container';
        fileInfo.innerHTML = `
            <i class="bi bi-file-earmark-text" aria-hidden="true"></i>
            <div>
                <strong>${escapeHtml(file.name)}</strong>
                <span class="file-size ms-2">(${formatFileSize(file.size)})</span>
            </div>
        `;

        // Remove button
        const removeBtn = document.createElement('button');
        removeBtn.className = 'btn btn-sm btn-outline-danger btn-remove';
        removeBtn.innerHTML = '<i class="bi bi-trash" aria-hidden="true"></i>';
        removeBtn.setAttribute('aria-label', `Eliminar ${file.name}`);
        removeBtn.onclick = () => removeFile(index);

        fileItem.appendChild(fileInfo);
        fileItem.appendChild(removeBtn);
        filesContainer.appendChild(fileItem);
    });

    // Update convert button text with file count
    updateConvertButton();
}

// ================================================
// Update Convert Button with File Count
// ================================================
function updateConvertButton() {
    const count = selectedFiles.length;
    if (fileCountSpan) {
        fileCountSpan.textContent = count === 1 ? 'Archivo' : `${count} Archivos`;
    }
    convertBtn.setAttribute('aria-label', `Convertir ${count} archivo${count > 1 ? 's' : ''} seleccionado${count > 1 ? 's' : ''}`);
}

// ================================================
// Remove File from List
// ================================================
function removeFile(index) {
    const fileName = selectedFiles[index].name;
    selectedFiles.splice(index, 1);

    if (selectedFiles.length === 0) {
        fileList.style.display = 'none';
        fileInput.value = '';
        updateAriaLive('Todos los archivos eliminados');
    } else {
        displayFileList();
        updateAriaLive(`${fileName} eliminado. ${selectedFiles.length} archivo${selectedFiles.length > 1 ? 's' : ''} restante${selectedFiles.length > 1 ? 's' : ''}`);
    }
}

// ================================================
// Format File Size
// ================================================
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ================================================
// Convert Files - Main Function
// ================================================
async function convertFiles() {
    if (selectedFiles.length === 0) return;

    // Disable convert button with loading state
    convertBtn.disabled = true;
    convertBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Convirtiendo...';

    // Show progress bar with animation
    progressArea.style.display = 'block';
    progressArea.classList.add('fade-in');
    updateProgress(0);
    updateProgressMessage(`Convirtiendo ${selectedFiles.length} archivo${selectedFiles.length > 1 ? 's' : ''}...`);
    updateAriaLive('Conversión iniciada');

    // Prepare form data
    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files[]', file);
    });

    try {
        // Simulate progress with smooth animation
        const progressInterval = setInterval(() => {
            const currentProgress = parseInt(progressBar.style.width);
            if (currentProgress < 90) {
                updateProgress(currentProgress + 10);
            }
        }, 200);

        // Send files to server
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);

        if (!response.ok) {
            throw new Error('Error en la conversión');
        }

        const result = await response.json();

        // Complete progress with celebration
        updateProgress(100);
        updateProgressMessage('¡Conversión completada!');

        // Show results after brief delay
        setTimeout(() => {
            displayResults(result);
            updateAriaLive(`Conversión completada. ${result.success} archivo${result.success > 1 ? 's' : ''} convertido${result.success > 1 ? 's' : ''}`);
        }, 500);

    } catch (error) {
        console.error('Error:', error);
        showError('Error al convertir archivos: ' + error.message);
        updateAriaLive('Error en la conversión');
        resetConvertButton();
    }
}

// ================================================
// Update Progress Bar
// ================================================
function updateProgress(percent) {
    progressBar.style.width = percent + '%';
    progressBar.setAttribute('aria-valuenow', percent);
    progressText.textContent = percent + '%';
}

function updateProgressMessage(message) {
    if (progressMessage) {
        progressMessage.textContent = message;
    }
}

// ================================================
// Display Results with Modern UI
// ================================================
function displayResults(result) {
    // Hide upload and progress areas
    fileList.style.display = 'none';
    progressArea.style.display = 'none';

    // Show results
    if (result.success > 0) {
        const plural = result.success > 1;
        resultsMessage.textContent = `Se ${plural ? 'convirtieron' : 'convirtió'} ${result.success} archivo${plural ? 's' : ''} exitosamente`;
        resultsArea.style.display = 'block';
        resultsArea.classList.add('fade-in');

        // Clear previous buttons
        downloadButtons.innerHTML = '';

        // Add individual download buttons
        result.results.forEach((file, index) => {
            const btnContainer = document.createElement('div');
            btnContainer.className = 'mb-2';
            btnContainer.style.animationDelay = `${index * 0.1}s`;

            const btn = document.createElement('a');
            btn.href = file.download_url;
            btn.className = 'btn btn-success btn-download w-100 fade-in';
            btn.setAttribute('download', file.original.replace('.msg', '.eml'));
            btn.innerHTML = `
                <i class="bi bi-download me-2" aria-hidden="true"></i>
                Descargar ${escapeHtml(file.original.replace('.msg', '.eml'))}
            `;

            btnContainer.appendChild(btn);
            downloadButtons.appendChild(btnContainer);
        });

        // Add batch download button if multiple files
        if (result.results.length > 1) {
            const batchBtnContainer = document.createElement('div');
            batchBtnContainer.className = 'mt-3';

            const batchBtn = document.createElement('button');
            batchBtn.className = 'btn btn-primary w-100 fade-in';
            batchBtn.innerHTML = '<i class="bi bi-file-zip me-2" aria-hidden="true"></i>Descargar Todos como ZIP';
            batchBtn.setAttribute('aria-label', `Descargar todos los ${result.results.length} archivos como ZIP`);
            batchBtn.onclick = () => downloadBatch(result.results);

            batchBtnContainer.appendChild(batchBtn);
            downloadButtons.appendChild(batchBtnContainer);
        }

        convertedFiles = result.results;
    }

    // Show errors if any
    if (result.errors > 0) {
        errorsArea.style.display = 'block';
        errorsArea.classList.add('fade-in');
        errorsList.innerHTML = '';

        result.error_details.forEach(error => {
            const errorItem = document.createElement('div');
            errorItem.className = 'mb-2';
            errorItem.innerHTML = `<strong>${escapeHtml(error.filename)}:</strong> ${escapeHtml(error.error)}`;
            errorsList.appendChild(errorItem);
        });
    }

    // Show reset button
    resetArea.style.display = 'block';
    resetArea.classList.add('fade-in');
}

// ================================================
// Download Batch as ZIP
// ================================================
async function downloadBatch(files) {
    try {
        const filenames = files.map(f => f.eml_filename);

        const response = await fetch('/batch-download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filenames })
        });

        if (!response.ok) {
            throw new Error('Error al crear el archivo ZIP');
        }

        // Download the zip file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'converted_emails.zip';
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();

        // Cleanup
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }, 100);

        updateAriaLive('Descarga de ZIP iniciada');

    } catch (error) {
        console.error('Error:', error);
        showError('Error al descargar archivos: ' + error.message);
        updateAriaLive('Error al descargar ZIP');
    }
}

// ================================================
// Show Error Message
// ================================================
function showError(message) {
    errorsArea.style.display = 'block';
    errorsArea.classList.add('fade-in');
    errorsList.innerHTML = `<p class="mb-0">${escapeHtml(message)}</p>`;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorsArea.style.display = 'none';
        errorsList.innerHTML = '';
    }, 5000);
}

// ================================================
// Reset Form to Initial State
// ================================================
function resetForm() {
    // Reset all variables
    selectedFiles = [];
    convertedFiles = [];

    // Reset file input
    fileInput.value = '';

    // Hide all dynamic areas
    fileList.style.display = 'none';
    progressArea.style.display = 'none';
    resultsArea.style.display = 'none';
    errorsArea.style.display = 'none';
    resetArea.style.display = 'none';

    // Reset button state
    resetConvertButton();

    // Clear containers
    filesContainer.innerHTML = '';
    downloadButtons.innerHTML = '';
    errorsList.innerHTML = '';

    // Reset progress
    updateProgress(0);
    updateProgressMessage('Convirtiendo archivos...');

    // Update accessibility
    updateAriaLive('Formulario reiniciado, listo para nueva conversión');

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ================================================
// Reset Convert Button
// ================================================
function resetConvertButton() {
    convertBtn.disabled = false;
    convertBtn.innerHTML = '<i class="bi bi-arrow-repeat me-2" aria-hidden="true"></i>Convertir Archivos';
}

// ================================================
// Utility: Escape HTML
// ================================================
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ================================================
// Performance: Debounce Function
// ================================================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ================================================
// Console Info
// ================================================
console.log('%c MSG to EML Converter ', 'background: #0078D4; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;');
console.log('%c Email Transformation Hub - 2025 ', 'background: #50E3C2; color: #1A1A1A; padding: 5px 10px; border-radius: 3px;');
console.log('Ready to convert your emails! 🚀');
