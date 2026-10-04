/**
 * GURUKUL AI Resume Screening System - Main JavaScript
 * Minimal, standard Vanilla JS utilities for Bootstrap 5 components and UX interactions.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Initialize Bootstrap Tooltips if any
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 2. Auto-dismiss alerts after 5 seconds
    const autoAlerts = document.querySelectorAll('.alert-dismissible');
    autoAlerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // 3. Reusable Delete / Destructive Action Confirmation modal helper
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function (button) {
        button.addEventListener('click', function (e) {
            const message = button.getAttribute('data-confirm') || 'Are you sure you want to perform this action?';
            if (!window.confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // 4. Password Visibility Toggle
    const toggleButtons = document.querySelectorAll('[data-password-toggle]');
    toggleButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const targetId = button.getAttribute('data-password-toggle');
            const targetInput = document.getElementById(targetId);
            if (targetInput) {
                const isPassword = targetInput.type === 'password';
                targetInput.type = isPassword ? 'text' : 'password';
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = isPassword ? 'bi bi-eye-slash-fill' : 'bi bi-eye-fill';
                }
            }
        });
    });

    // 5. Submit Button Loading & Disabled State
    const submitForms = document.querySelectorAll('form[data-loading-form]');
    submitForms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!form.checkValidity()) {
                return;
            }
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                // Delay disabling slightly so browser submits the form properly
                setTimeout(function () {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="gk-loading-spinner me-2" style="width: 1rem; height: 1rem; border-color: rgba(255,255,255,0.3); border-top-color: #fff; vertical-align: middle;"></span> Processing...';
                }, 10);
            }
        });
    });
});
