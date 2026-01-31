/**
 * Frontend Logic para Minecraft Transpiler
 */

const API_BASE = 'http://localhost:5000/api';

let currentJobId = null;
let statusCheckInterval = null;

// ============================================================================
// ELEMENTOS DOM
// ============================================================================

const uploadSection = document.getElementById('uploadSection');
const processingSection = document.getElementById('processingSection');
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');

const processingTitle = document.getElementById('processingTitle');
const processingStatus = document.getElementById('processingStatus');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const fileName = document.getElementById('fileName');
const statusMessage = document.getElementById('statusMessage');

const statsSection = document.getElementById('statsSection');
const statItems = document.getElementById('statItems');
const statRecipes = document.getElementById('statRecipes');
const statScripts = document.getElementById('statScripts');
const statAssets = document.getElementById('statAssets');

const actionsSection = document.getElementById('actionsSection');
const downloadBtn = document.getElementById('downloadBtn');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');

// ============================================================================
// EVENT LISTENERS
// ============================================================================

// Upload via input
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

// Drag & Drop
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('drag-over');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    
    if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
    }
});

// Click no upload box
uploadBox.addEventListener('click', () => {
    fileInput.click();
});

// ============================================================================
// FUNÇÕES PRINCIPAIS
// ============================================================================

async function handleFileUpload(file) {
    // Validação
    if (!file.name.endsWith('.jar')) {
        alert('❌ Por favor, selecione um arquivo .jar');
        return;
    }
    
    if (file.size > 100 * 1024 * 1024) {
        alert('❌ Arquivo muito grande! Máximo: 100MB');
        return;
    }
    
    // Prepara FormData
    const formData = new FormData();
    formData.append('file', file);
    
    // Mostra seção de processamento
    uploadSection.classList.add('hidden');
    processingSection.classList.remove('hidden');
    
    fileName.textContent = file.name;
    processingTitle.textContent = 'Enviando arquivo...';
    processingStatus.textContent = 'Aguarde...';
    
    try {
        // Upload
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro no upload');
        }
        
        const data = await response.json();
        currentJobId = data.job_id;
        
        // Inicia monitoramento
        startStatusCheck();
        
    } catch (error) {
        showError(error.message);
    }
}

function startStatusCheck() {
    processingTitle.textContent = 'Processando mod...';
    
    statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/status/${currentJobId}`);
            
            if (!response.ok) {
                throw new Error('Erro ao verificar status');
            }
            
            const data = await response.json();
            updateProgress(data);
            
            // Verifica conclusão
            if (data.status === 'completed') {
                clearInterval(statusCheckInterval);
                showCompletion(data);
            } else if (data.status === 'failed') {
                clearInterval(statusCheckInterval);
                showError(data.error || 'Erro desconhecido');
            }
            
        } catch (error) {
            clearInterval(statusCheckInterval);
            showError(error.message);
        }
    }, 1000); // Verifica a cada 1 segundo
}

function updateProgress(data) {
    const progress = data.progress || 0;
    
    // Atualiza barra de progresso
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
    
    // Atualiza mensagens
    processingStatus.textContent = data.message || 'Processando...';
    statusMessage.textContent = data.status === 'processing' ? 
        '🔄 Em andamento...' : 
        '⏳ Aguardando...';
}

function showCompletion(data) {
    processingTitle.textContent = '✅ Conversão Concluída!';
    processingStatus.textContent = 'Seu addon está pronto!';
    statusMessage.textContent = '✅ Sucesso';
    
    progressFill.style.width = '100%';
    progressText.textContent = '100%';
    
    // Mostra estatísticas
    if (data.stats) {
        statsSection.classList.remove('hidden');
        statItems.textContent = data.stats.items_processed || 0;
        statRecipes.textContent = data.stats.recipes_converted || 0;
        statScripts.textContent = data.stats.scripts_generated || 0;
        statAssets.textContent = data.stats.assets_extracted || 0;
    }
    
    // Mostra botões de ação
    actionsSection.classList.remove('hidden');
    
    // Configura download
    downloadBtn.onclick = () => {
        window.location.href = `${API_BASE}/download/${currentJobId}`;
    };
}

function showError(message) {
    processingTitle.textContent = '❌ Erro no Processamento';
    processingStatus.textContent = 'Algo deu errado';
    statusMessage.textContent = '❌ Falhou';
    
    errorMessage.classList.remove('hidden');
    errorText.textContent = message;
}

function resetForm() {
    // Reseta estado
    currentJobId = null;
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
    
    // Reseta UI
    processingSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    
    statsSection.classList.add('hidden');
    actionsSection.classList.add('hidden');
    errorMessage.classList.add('hidden');
    
    progressFill.style.width = '0%';
    progressText.textContent = '0%';
    
    fileInput.value = '';
}

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

console.log('🚀 Minecraft Transpiler Frontend iniciado');
