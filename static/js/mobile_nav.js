// Global profile dropdown toggle function
window.toggleProfileDropdown = function (e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    const profileDropdown = document.getElementById('profileDropdownCard');
    if (profileDropdown) {
        profileDropdown.classList.toggle('open');
    }
};

document.addEventListener('DOMContentLoaded', function () {
    const hamburger = document.getElementById('hamburgerBtn');
    const sidebar = document.getElementById('mobileSidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    const closeBtn = document.getElementById('sidebarCloseBtn');

    function openSidebar() {
        if (sidebar && backdrop) {
            sidebar.classList.add('open');
            backdrop.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    function closeSidebar() {
        if (sidebar && backdrop) {
            sidebar.classList.remove('open');
            backdrop.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    if (hamburger) {
        hamburger.addEventListener('click', openSidebar);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeSidebar);
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }

    // Close on escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if (sidebar && sidebar.classList.contains('open')) {
                closeSidebar();
            }
            const profileDropdown = document.getElementById('profileDropdownCard');
            if (profileDropdown && profileDropdown.classList.contains('open')) {
                profileDropdown.classList.remove('open');
            }
        }
    });

    // Click outside handler to dismiss profile dropdown
    document.addEventListener('click', function (e) {
        const avatarBtn = document.getElementById('userAvatarBtn');
        const profileDropdown = document.getElementById('profileDropdownCard');
        if (profileDropdown && profileDropdown.classList.contains('open')) {
            if (avatarBtn && avatarBtn.contains(e.target)) {
                return;
            }
            if (!profileDropdown.contains(e.target)) {
                profileDropdown.classList.remove('open');
            }
        }
    });
});
