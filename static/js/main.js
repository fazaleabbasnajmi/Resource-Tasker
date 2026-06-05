// Sidebar toggle (mobile)
const mobileToggle = document.getElementById('mobileToggle');
const sidebar = document.getElementById('sidebar');

if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });
    // Close sidebar when clicking outside
    document.addEventListener('click', (e) => {
        if (sidebar.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            e.target !== mobileToggle) {
            sidebar.classList.remove('open');
        }
    });
}

// Auto-dismiss flash messages after 4s
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
        alert.style.transition = 'opacity .4s';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 400);
    }, 4000);
});

// Highlight active nav item based on current path
document.querySelectorAll('.nav-item').forEach(item => {
    if (item.href === window.location.href) {
        item.classList.add('active');
    }
});

// Set today as min date for due date inputs
document.querySelectorAll('input[type=date]').forEach(input => {
    if (!input.value) {
        // Don't force min, just set a reasonable default placeholder
    }
});

