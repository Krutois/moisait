(function() {
    let recognition = null;
    let isRecording = false;
    let finalText = "";
    let interimText = "";

    const textDiv = document.getElementById('subtitlesText');
    const startBtn = document.getElementById('startSubtitlesBtn');
    const stopBtn = document.getElementById('stopSubtitlesBtn');
    const clearBtn = document.getElementById('clearSubtitlesBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const exitBtn = document.getElementById('exitSubtitlesBtn');
    const langSelect = document.getElementById('subLangSelect');
    const statusDiv = document.getElementById('subtitlesStatus');

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        textDiv.innerText = "❌ Ваш браузер не поддерживает распознавание речи";
        startBtn.disabled = true;
        return;
    }

    function updateDisplay() {
        const display = (finalText + (interimText ? " " + interimText : "")).trim();
        textDiv.innerText = display || "🎤 Говорите...";
    }

    function initRecognition() {
        const recog = new SpeechRecognition();
        recog.interimResults = true;
        recog.continuous = true;
        recog.lang = langSelect.value;
        recog.onresult = (event) => {
            interimText = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) finalText += transcript + " ";
                else interimText = transcript;
            }
            updateDisplay();
        };
        recog.onerror = (e) => {
            if (e.error === 'not-allowed') statusDiv.innerText = "❌ Нет доступа к микрофону";
            else statusDiv.innerText = "❌ Ошибка: " + e.error;
            stopRecording();
        };
        recog.onend = () => { if (isRecording) stopRecording(); };
        return recog;
    }

    async function startRecording() {
        if (isRecording) return;
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch {
            statusDiv.innerText = "❌ Микрофон недоступен";
            return;
        }
        recognition = initRecognition();
        recognition.start();
        isRecording = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        statusDiv.innerText = "🎙️ Слушаю...";
    }

    function stopRecording() {
        if (!isRecording) return;
        if (recognition) recognition.stop();
        isRecording = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        statusDiv.innerText = "⏸ Остановлено";
    }

    function clearText() {
        finalText = "";
        interimText = "";
        updateDisplay();
        statusDiv.innerText = "Текст очищен";
        setTimeout(() => { if (!isRecording) statusDiv.innerText = "Готов"; }, 1500);
    }

    function toggleFullscreen() {
        const elem = document.getElementById('subtitlesMode');
        if (!document.fullscreenElement) {
            elem.requestFullscreen().catch(err => console.warn(err));
        } else {
            document.exitFullscreen();
        }
    }

    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    clearBtn.addEventListener('click', clearText);
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    exitBtn.addEventListener('click', () => window.location.href = "/");

    langSelect.addEventListener('change', () => {
        if (isRecording) { stopRecording(); startRecording(); }
    });
})();