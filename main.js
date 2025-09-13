// Main JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');

            // Remove active class from all buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');

            // Hide all tab contents
            tabContents.forEach(content => content.style.display = 'none');
            // Show selected tab content
            const selectedTab = document.getElementById(tabId);
            if (selectedTab) {
                selectedTab.style.display = 'block';
            }
        });
    });

    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const fileName = file.name;
                const fileSize = (file.size / 1024 / 1024).toFixed(2) + ' MB';

                // Find the associated label or display element
                const label = this.nextElementSibling;
                if (label && label.tagName === 'LABEL') {
                    label.textContent = `${fileName} (${fileSize})`;
                }
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.style.borderColor = '#dc2626';
                    isValid = false;
                } else {
                    field.style.borderColor = '#e1e5e9';
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });

    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);

            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Job card hover effects
    const jobCards = document.querySelectorAll('.job-card');
    jobCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px) scale(1.01)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Search functionality
    const searchInput = document.getElementById('search-input');
    const locationFilter = document.getElementById('location-filter');
    const typeFilter = document.getElementById('type-filter');

    function filterJobs() {
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        const locationValue = locationFilter ? locationFilter.value : 'All';
        const typeValue = typeFilter ? typeFilter.value : 'All';

        const jobCards = document.querySelectorAll('.job-card');

        jobCards.forEach(card => {
            const title = card.querySelector('.job-title')?.textContent.toLowerCase() || '';
            const company = card.querySelector('.job-meta')?.textContent.toLowerCase() || '';
            const location = card.querySelector('.job-meta')?.textContent.toLowerCase() || '';
            const type = card.querySelector('.job-meta')?.textContent.toLowerCase() || '';

            const matchesSearch = !searchTerm ||
                title.includes(searchTerm) ||
                company.includes(searchTerm);

            const matchesLocation = locationValue === 'All' || location.includes(locationValue.toLowerCase());
            const matchesType = typeValue === 'All' || type.includes(typeValue.toLowerCase());

            if (matchesSearch && matchesLocation && matchesType) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    if (searchInput) searchInput.addEventListener('input', filterJobs);
    if (locationFilter) locationFilter.addEventListener('change', filterJobs);
    if (typeFilter) typeFilter.addEventListener('change', filterJobs);

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 300);
        }, 5000);
    });

    // Code editor functionality
    const codeEditors = document.querySelectorAll('.code-area');
    codeEditors.forEach(editor => {
        editor.addEventListener('keydown', function(e) {
            // Handle Tab key for indentation
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = this.selectionStart;
                const end = this.selectionEnd;
                this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
                this.selectionStart = this.selectionEnd = start + 4;
            }
        });
    });

    // Run code button functionality
    const runButtons = document.querySelectorAll('.run-button');
    runButtons.forEach(button => {
        button.addEventListener('click', function() {
            const editor = this.closest('.code-editor').querySelector('.code-area');
            const outputArea = this.closest('.code-editor').querySelector('.output-area');

            if (editor && outputArea) {
                const code = editor.value;
                // This would need to be handled by the server
                // For now, just show a placeholder
                outputArea.textContent = 'Code execution would happen here...';
                outputArea.classList.remove('output-error');
            }
        });
    });
});