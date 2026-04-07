const form = document.getElementById('settingsForm');
const messageDiv = document.getElementById('settingsMessage');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const payload = { username, email };
    if (password) payload.password = password;
    const res = await fetch('/api/user', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
        messageDiv.innerHTML = '<div class="text-green-400">Profile updated successfully</div>';
        setTimeout(() => location.reload(), 1500);
    } else {
        messageDiv.innerHTML = `<div class="text-red-400">${data.error}</div>`;
    }
});