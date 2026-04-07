(function() {
    const steps = [
        { element: '#recordBtn', title: '🎤 Запись речи', description: 'Нажмите на микрофон, чтобы начать распознавание речи. Разрешите доступ к микрофону.', position: 'bottom' },
        { element: '#languageSelect', title: '🌐 Выбор языка', description: 'Вы можете распознавать речь на русском, казахском или английском.', position: 'bottom' },
        { element: '#resultText', title: '📝 Текст в реальном времени', description: 'Распознанный текст появляется здесь мгновенно. Вы можете копировать, скачивать или очищать его.', position: 'top' },
        { element: '.history-link', title: '📜 История', description: 'Все ваши транскрипции сохраняются в разделе "История". Там можно искать, фильтровать и удалять записи.', position: 'bottom', customSelector: true },
        { element: '.ai-functions', title: '✨ AI-функции', description: 'После распознавания вы можете исправить текст, перефразировать, перевести или сократить его с помощью искусственного интеллекта.', position: 'top', customSelector: true }
    ];

    let currentStep = 0, overlay, popup, isActive = false;

    function createOverlay() {
        if (overlay) return;
        overlay = document.createElement('div');
        overlay.className = 'onboarding-overlay';
        document.body.appendChild(overlay);
    }
    function createPopup() {
        popup = document.createElement('div');
        popup.className = 'onboarding-popup glass';
        popup.innerHTML = `
            <div class="onboarding-popup-header"><h3></h3><button class="onboarding-close">✕</button></div>
            <p class="onboarding-description"></p>
            <div class="onboarding-popup-footer">
                <button class="onboarding-prev btn-secondary">Назад</button>
                <span class="onboarding-counter"></span>
                <button class="onboarding-next btn-premium">Далее</button>
            </div>
        `;
        document.body.appendChild(popup);
        popup.querySelector('.onboarding-close').addEventListener('click', finish);
        popup.querySelector('.onboarding-prev').addEventListener('click', prev);
        popup.querySelector('.onboarding-next').addEventListener('click', next);
    }
    function getElement(step) {
        return step.customSelector ? document.querySelector(step.element) : document.getElementById(step.element.substring(1));
    }
    function highlight(step) {
        document.querySelectorAll('.onboarding-highlight').forEach(el => el.classList.remove('onboarding-highlight'));
        const el = getElement(step);
        if (el) { el.classList.add('onboarding-highlight'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
        return el;
    }
    function positionPopup(el, step) {
        if (!el || !popup) return;
        const rect = el.getBoundingClientRect(), pr = popup.getBoundingClientRect();
        let top = (step.position === 'top') ? rect.top - pr.height - 10 : rect.bottom + 10;
        let left = rect.left + rect.width/2 - pr.width/2;
        if (top < 10) top = rect.bottom + 10;
        if (top + pr.height > window.innerHeight-10) top = rect.top - pr.height - 10;
        if (left < 10) left = 10;
        if (left + pr.width > window.innerWidth-10) left = window.innerWidth - pr.width - 10;
        popup.style.top = `${top}px`;
        popup.style.left = `${left}px`;
    }
    function showStep(index) {
        if (index < 0 || index >= steps.length) return finish();
        currentStep = index;
        const step = steps[currentStep];
        const el = highlight(step);
        if (!el) return next();
        popup.querySelector('.onboarding-popup-header h3').innerText = step.title;
        popup.querySelector('.onboarding-description').innerText = step.description;
        popup.querySelector('.onboarding-counter').innerText = `${currentStep+1}/${steps.length}`;
        popup.querySelector('.onboarding-prev').style.display = currentStep===0 ? 'none' : 'inline-block';
        popup.querySelector('.onboarding-next').innerText = currentStep===steps.length-1 ? 'Завершить' : 'Далее';
        positionPopup(el, step);
        popup.classList.add('active');
        overlay.classList.add('active');
        isActive = true;
    }
    function next() { if (currentStep < steps.length-1) showStep(currentStep+1); else finish(); }
    function prev() { if (currentStep > 0) showStep(currentStep-1); }
    function finish() {
        if (popup) popup.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
        isActive = false;
        document.querySelectorAll('.onboarding-highlight').forEach(el => el.classList.remove('onboarding-highlight'));
        localStorage.setItem('onboardingCompleted', 'true');
    }
    function start() {
        if (isActive) return;
        createOverlay(); createPopup(); showStep(0);
    }
    if (!localStorage.getItem('onboardingCompleted')) {
        document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', start) : start();
    }
    window.restartOnboarding = start;
})();