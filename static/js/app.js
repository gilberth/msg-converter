// MSG to EML Converter - Frontend JavaScript

let selectedFiles = [];
let convertedFiles = [];

// DOM Elements
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const filesContainer = document.getElementById('files-container');
const convertBtn = document.getElementById('convert-btn');
const progressArea = document.getElementById('progress-area');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const resultsArea = document.getElementById('results-area');
const resultsMessage = document.getElementById('results-message');
const downloadButtons = document.getElementById('download-buttons');
const errorsArea = document.getElementById('errors-area');
const errorsList = document.getElementById('errors-list');
const resetArea = document.getElementById('reset-area');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFiles(files);
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');

    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
}

function addFiles(files) {
    // Filter MSG files only
    const msgFiles = files.filter(file => file.name.toLowerCase().endsWith('.msg'));

    if (msgFiles.length === 0) {
        showError('Por favor selecciona archivos MSG válidos');
        return;
    }

    selectedFiles = [...selectedFiles, ...msgFiles];
    displayFileList();
    fileList.style.display = 'block';
    fileList.classList.add('fade-in');
}

function displayFileList() {
    filesContainer.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'list-group-item d-flex justify-content-between align-items-center fade-in';

        const fileInfo = document.createElement('div');
        fileInfo.innerHTML = `
            <i class="bi bi-file-earmark-text text-primary me-2"></i>
            <strong>${file.name}</strong>
            <span class="file-size ms-2">(${formatFileSize(file.size)})</span>
        `;

        const removeBtn = document.createElement('button');
        removeBtn.className = 'btn btn-sm btn-outline-danger btn-remove';
        removeBtn.innerHTML = '<i class="bi bi-trash"></i>';
        removeBtn.onclick = () => removeFile(index);

        fileItem.appendChild(fileInfo);
        fileItem.appendChild(removeBtn);
        filesContainer.appendChild(fileItem);
    });
}

function removeFile(index) {
    selectedFiles.splice(index, 1);

    if (selectedFiles.length === 0) {
        fileList.style.display = 'none';
        fileInput.value = '';
    } else {
        displayFileList();
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

async function convertFiles() {
    if (selectedFiles.length === 0) return;

    // Disable convert button
    convertBtn.disabled = true;
    convertBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Convirtiendo...';

    // Show progress bar
    progressArea.style.display = 'block';
    progressArea.classList.add('fade-in');
    updateProgress(0);

    // Prepare form data
    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files[]', file);
    });

    try {
        // Simulate progress
        const progressInterval = setInterval(() => {
            const currentProgress = parseInt(progressBar.style.width);
            if (currentProgress < 90) {
                updateProgress(currentProgress + 10);
            }
        }, 200);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);

        if (!response.ok) {
            throw new Error('Error en la conversión');
        }

        const result = await response.json();

        // Complete progress
        updateProgress(100);

        // Show results
        setTimeout(() => {
            displayResults(result);
        }, 500);

    } catch (error) {
        console.error('Error:', error);
        showError('Error al convertir archivos: ' + error.message);
        resetForm();
    }
}

function updateProgress(percent) {
    progressBar.style.width = percent + '%';
    progressText.textContent = percent + '%';
}

function displayResults(result) {
    // Hide upload and progress areas
    fileList.style.display = 'none';
    progressArea.style.display = 'none';

    // Show results
    if (result.success > 0) {
        resultsMessage.textContent = `Se convirtieron ${result.success} archivo(s) exitosamente`;
        resultsArea.style.display = 'block';
        resultsArea.classList.add('fade-in');

        // Add download buttons
        downloadButtons.innerHTML = '';

        result.results.forEach(file => {
            const btnContainer = document.createElement('div');
            btnContainer.className = 'mb-2';

            const btn = document.createElement('a');
            btn.href = file.download_url;
            btn.className = 'btn btn-success btn-download w-100';
            btn.innerHTML = `
                <i class="bi bi-download me-2"></i>
                Descargar ${file.original.replace('.msg', '.eml')}
            `;

            btnContainer.appendChild(btn);
            downloadButtons.appendChild(btnContainer);
        });

        // Add batch download if multiple files
        if (result.results.length > 1) {
            const batchBtn = document.createElement('button');
            batchBtn.className = 'btn btn-primary w-100 mt-2';
            batchBtn.innerHTML = '<i class="bi bi-file-zip me-2"></i>Descargar Todos (ZIP)';
            batchBtn.onclick = () => downloadBatch(result.results);
            downloadButtons.appendChild(batchBtn);
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
            errorItem.innerHTML = `<strong>${error.filename}:</strong> ${error.error}`;
            errorsList.appendChild(errorItem);
        });
    }

    // Show reset button
    resetArea.style.display = 'block';
    resetArea.classList.add('fade-in');
}

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
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

    } catch (error) {
        console.error('Error:', error);
        alert('Error al descargar archivos: ' + error.message);
    }
}

function showError(message) {
    errorsArea.style.display = 'block';
    errorsArea.classList.add('fade-in');
    errorsList.innerHTML = `<p class="mb-0">${message}</p>`;

    setTimeout(() => {
        errorsArea.style.display = 'none';
    }, 5000);
}

function resetForm() {
    // Reset all variables
    selectedFiles = [];
    convertedFiles = [];

    // Reset file input
    fileInput.value = '';

    // Hide all areas
    fileList.style.display = 'none';
    progressArea.style.display = 'none';
    resultsArea.style.display = 'none';
    errorsArea.style.display = 'none';
    resetArea.style.display = 'none';

    // Reset button
    convertBtn.disabled = false;
    convertBtn.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i>Convertir Archivos';

    // Clear containers
    filesContainer.innerHTML = '';
    downloadButtons.innerHTML = '';
    errorsList.innerHTML = '';

    // Reset progress
    updateProgress(0);
}
