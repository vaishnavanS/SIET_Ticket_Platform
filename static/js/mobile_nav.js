// Global profile dropdown toggle function
window.toggleProfileDropdown = function (e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    const profileDropdown = document.getElementById('profileDropdownCard');
    const notifDropdown = document.getElementById('notifDropdownCard');
    if (notifDropdown) {
        notifDropdown.classList.remove('open');
        notifDropdown.style.display = 'none';
    }
    if (profileDropdown) {
        const isOpen = profileDropdown.classList.contains('open');
        if (isOpen) {
            profileDropdown.classList.remove('open');
            profileDropdown.style.display = 'none';
        } else {
            profileDropdown.classList.add('open');
            profileDropdown.style.display = 'block';
        }
    }
};

// Global notification dropdown toggle function
window.toggleNotifDropdown = function (e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    const notifDropdown = document.getElementById('notifDropdownCard');
    const profileDropdown = document.getElementById('profileDropdownCard');
    if (profileDropdown) {
        profileDropdown.classList.remove('open');
        profileDropdown.style.display = 'none';
    }
    if (notifDropdown) {
        const isOpen = notifDropdown.classList.contains('open');
        if (isOpen) {
            notifDropdown.classList.remove('open');
            notifDropdown.style.display = 'none';
        } else {
            notifDropdown.classList.add('open');
            notifDropdown.style.display = 'flex';
        }
    }
};

// Global mobile sidebar notifications toggle function
window.toggleSidebarNotifs = function (e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    const panel = document.getElementById('sidebarNotifPanel');
    const accordion = document.getElementById('sidebarNotifAccordion') || (panel ? panel.closest('.sidebar-notif-accordion') : null);
    if (panel) {
        const isCurrentlyOpen = panel.classList.contains('open') || panel.style.display === 'block';
        if (isCurrentlyOpen) {
            panel.classList.remove('open');
            panel.style.display = 'none';
            if (accordion) accordion.classList.remove('open');
        } else {
            panel.classList.add('open');
            panel.style.display = 'block';
            if (accordion) accordion.classList.add('open');
        }
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
            if (profileDropdown) {
                profileDropdown.classList.remove('open');
                profileDropdown.style.display = 'none';
            }
            const notifDropdown = document.getElementById('notifDropdownCard');
            if (notifDropdown) {
                notifDropdown.classList.remove('open');
                notifDropdown.style.display = 'none';
            }
        }
    });

    // Click outside handler to dismiss profile & notification dropdowns
    document.addEventListener('click', function (e) {
        const avatarBtn = document.getElementById('userAvatarBtn');
        const profileDropdown = document.getElementById('profileDropdownCard');
        if (profileDropdown && (profileDropdown.classList.contains('open') || profileDropdown.style.display === 'block')) {
            if (avatarBtn && avatarBtn.contains(e.target)) {
                return;
            }
            if (!profileDropdown.contains(e.target)) {
                profileDropdown.classList.remove('open');
                profileDropdown.style.display = 'none';
            }
        }

        const notifBellBtn = document.getElementById('notifBellBtn');
        const notifDropdown = document.getElementById('notifDropdownCard');
        if (notifDropdown && (notifDropdown.classList.contains('open') || notifDropdown.style.display === 'flex')) {
            if (notifBellBtn && notifBellBtn.contains(e.target)) {
                return;
            }
            if (!notifDropdown.contains(e.target)) {
                notifDropdown.classList.remove('open');
                notifDropdown.style.display = 'none';
            }
        }
    });
});
