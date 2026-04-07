(function() {
    let recognition = null;
    let isRecording = false;
    let fullText = "";
    let startTime = null;
    let timerInterval = null;

    const recordBtn = document.getElementById('recordBtn');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const copyBtn = document.getElementById('copyBtn');
    const clearBtn = document.getElementById('clearBtn');
    const downloadTxtBtn = document.getElementById('downloadTxtBtn');
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    const langSelect = document.getElementById('languageSelect');
    const statusSpan = document.getElementById('statusText');
    const wordCountSpan = document.getElementById('wordCount');
    const timerDisplay = document.getElementById('timerDisplay');
    const transcriptionDiv = document.getElementById('transcriptionText');

    // Check browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        statusSpan.innerText = "❌ Браузер не поддерживает распознавание речи";
        recordBtn.disabled = true;
        startBtn.disabled = true;
        return;
    }

    function updateStats() {
        const words = fullText.trim().split(/\s+/).filter(w => w).length;
        wordCountSpan.innerText = words;
        if (startTime) {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const mins = Math.floor(elapsed / 60);
            const secs = elapsed % 60;
            timerDisplay.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
    }

    function updateTranscription(text) {
        fullText = text;
        transcriptionDiv.innerText = text || "Здесь появится распознанный текст...";
        updateStats();
        // Auto-scroll to bottom
        transcriptionDiv.scrollTop = transcriptionDiv.scrollHeight;
    }

    function initRecognition() {
        const recog = new SpeechRecognition();
        recog.interimResults = true;
        recog.continuous = true;
        recog.lang = langSelect.value;
        recog.onresult = (event) => {
            let interim = "", final = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) final += transcript + " ";
                else interim += transcript;
            }
            const displayText = (fullText + final + interim).trim();
            transcriptionDiv.innerText = displayText || "Здесь появится распознанный текст...";
            transcriptionDiv.scrollTop = transcriptionDiv.scrollHeight;
            // Store final text for later saving
            if (final) fullText += final;
        };
        recog.onerror = (e) => {
            console.error(e);
            if (e.error === 'not-allowed') {
                statusSpan.innerText = "❌ Нет доступа к микрофону";
            } else {
                statusSpan.innerText = "❌ Ошибка: " + e.error;
            }
            stopRecording();
        };
        recog.onend = () => {
            if (isRecording) stopRecording();
        };
        return recog;
    }

    async function startRecording() {
        if (isRecording) return;
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (err) {
            statusSpan.innerText = "❌ Микрофон недоступен";
            return;
        }
        recognition = initRecognition();
        recognition.start();
        isRecording = true;
        startTime = Date.now();
        timerInterval = setInterval(updateStats, 1000);
        statusSpan.innerText = "🎙️ Слушаю...";
        recordBtn.classList.add('mic-active');
        startBtn.disabled = true;
        stopBtn.disabled = false;
        fullText = "";
        updateTranscription("");
    }

    async function stopRecording() {
        if (!isRecording) return;
        if (recognition) recognition.stop();
        isRecording = false;
        if (timerInterval) clearInterval(timerInterval);
        statusSpan.innerText = "Idle";
        recordBtn.classList.remove('mic-active');
        startBtn.disabled = false;
        stopBtn.disabled = true;
        const text = fullText.trim();
        if (text) {
            // Save to backend
            try {
                await fetch('/api/transcribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        language: langSelect.value.split('-')[0],
                        duration: startTime ? Math.floor((Date.now() - startTime) / 1000) : 0
                    })
                });
                showToast("✅ Сохранено в историю", "success");
            } catch (err) {
                console.error(err);
                showToast("❌ Ошибка сохранения", "error");
            }
        }
    }

    function showToast(msg, type = "info") {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.innerText = msg;
        toast.className = `glass px-6 py-3 rounded-full text-white animate-fadeIn toast-${type}`;
        toast.setAttribute('role', 'status');
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // Event listeners
    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    recordBtn.addEventListener('click', startRecording); // optional: mic click also starts

    copyBtn.addEventListener('click', () => {
        if (fullText) {
            navigator.clipboard.writeText(fullText);
            showToast("📋 Скопировано", "success");
        } else {
            showToast("Нет текста для копирования", "info");
        }
    });

    clearBtn.addEventListener('click', () => {
        fullText = "";
        updateTranscription("");
        showToast("🧹 Текст очищен", "info");
    });

    downloadTxtBtn.addEventListener('click', () => {
        if (!fullText) { showToast("Нет текста для скачивания", "info"); return; }
        const blob = new Blob([fullText], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'transcript.txt';
        a.click();
        URL.revokeObjectURL(a.href);
        showToast("📄 Скачано TXT", "success");
    });

    downloadPdfBtn.addEventListener('click', async () => {
        if (!fullText) { showToast("Нет текста для скачивания", "info"); return; }
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        doc.text(fullText, 10, 10);
        doc.save('transcript.pdf');
        showToast("📑 Скачано PDF", "success");
    });

    langSelect.addEventListener('change', () => {
        if (isRecording) stopRecording();
    });
})();