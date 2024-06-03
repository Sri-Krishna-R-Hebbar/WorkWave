function toggleForm() {
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const toggleButton = document.querySelector('.toggle-button');

    if (loginForm.style.display === 'none') {
        loginForm.style.display = 'block';
        signupForm.style.display = 'none';
        toggleButton.textContent = 'Signup';
    } else {
        loginForm.style.display = 'none';
        signupForm.style.display = 'block';
        toggleButton.textContent = 'Login';
    }
}