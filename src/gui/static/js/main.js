// Main JavaScript for ToolAI
// Định nghĩa hàm khởi tạo các sự kiện
function initializeEvents() {
    // Form validation
    const commandForm = document.querySelector('.command-form');
    if (commandForm) {
        // Xóa event listener cũ nếu có
        const newCommandForm = commandForm.cloneNode(true);
        commandForm.parentNode.replaceChild(newCommandForm, commandForm);
        
        newCommandForm.addEventListener('submit', function(e) {
            const commandTextarea = document.getElementById('command');
            if (!commandTextarea.value.trim()) {
                e.preventDefault();
                commandTextarea.classList.add('error');

                // Create error message if it doesn't exist
                let errorMsg = commandTextarea.nextElementSibling;
                if (!errorMsg || !errorMsg.classList.contains('error-message')) {
                    errorMsg = document.createElement('div');
                    errorMsg.classList.add('error-message');
                    errorMsg.textContent = 'Vui lòng nhập lệnh trước khi thực thi';
                    commandTextarea.parentNode.insertBefore(errorMsg, commandTextarea.nextSibling);
                }

                // Focus and remove error on input
                commandTextarea.focus();
                commandTextarea.addEventListener('input', function() {
                    if (this.value.trim()) {
                        this.classList.remove('error');
                        if (errorMsg) errorMsg.remove();
                    }
                }, { once: true });
            }
        });
    }

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.btn-icon[title="Sao chép"]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const resultContent = document.getElementById('result-content');
            if (resultContent && resultContent.textContent) {
                navigator.clipboard.writeText(resultContent.textContent)
                    .then(() => {
                        // Show copied notification
                        const notification = document.createElement('div');
                        notification.classList.add('toast-notification');
                        notification.textContent = 'Đã sao chép vào clipboard';
                        document.body.appendChild(notification);

                        // Remove notification after 2 seconds
                        setTimeout(() => {
                            notification.classList.add('fade-out');
                            setTimeout(() => {
                                notification.remove();
                            }, 300);
                        }, 2000);
                    })
                    .catch(err => {
                        console.error('Không thể sao chép: ', err);
                    });
            }
        });
    });

    // History item rerun functionality
    const rerunButtons = document.querySelectorAll('.history-actions .btn-icon[title="Chạy lại"]');
    rerunButtons.forEach(button => {
        button.addEventListener('click', function() {
            const historyItem = this.closest('.history-item');
            const command = historyItem.querySelector('.history-command').textContent;

            // Fill command in the form
            const commandTextarea = document.getElementById('command');
            if (commandTextarea) {
                commandTextarea.value = command;
                commandTextarea.focus();

                // Scroll to command form
                const commandCard = document.querySelector('.command-card');
                if (commandCard) {
                    commandCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });
    
    // Add animations for elements when they come into view
    const elements = document.querySelectorAll('.stat-card, .command-card, .output-card, .history-card');
    elements.forEach(element => {
        const elementPosition = element.getBoundingClientRect().top;
        const windowHeight = window.innerHeight;

        if (elementPosition < windowHeight - 50) {
            element.classList.add('animated');
        }
    });

    // Add pulse effect to buttons
    const primaryButtons = document.querySelectorAll('.btn-primary');
    primaryButtons.forEach(button => {
        button.addEventListener('mouseover', function() {
            this.classList.add('pulse');
        });

        button.addEventListener('animationend', function() {
            this.classList.remove('pulse');
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Thêm nút làm mới trang vào header
    const headerRight = document.querySelector('.header-right');
    if (headerRight) {
        const refreshButton = document.createElement('button');
        refreshButton.id = 'refreshPage';
        refreshButton.className = 'refresh-btn';
        refreshButton.title = 'Làm mới giao diện';
        refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
        
        // Thêm vào đầu header-right
        if (headerRight.firstChild) {
            headerRight.insertBefore(refreshButton, headerRight.firstChild);
        } else {
            headerRight.appendChild(refreshButton);
        }
        
        // Thêm sự kiện click để làm mới trang
        refreshButton.addEventListener('click', function() {
            // Thêm hiệu ứng quay khi đang tải
            this.classList.add('refreshing');
            
            // Cách 1: Tải lại toàn bộ trang (đơn giản nhưng mất trạng thái hiện tại)
            // location.reload();
            
            // Cách 2: Chỉ tải lại template mà không tải lại toàn bộ trang (giữ trạng thái)
            fetch('/api/reload-template?template=index.html')
                .then(response => response.text())
                .then(html => {
                    // Chỉ thay thế phần nội dung chính
                    const contentElement = document.querySelector('.content');
                    if (contentElement) {
                        // Tạo một div tạm thời để phân tích nội dung HTML
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = html;
                        
                        // Lấy phần nội dung từ template mới
                        const newContent = tempDiv.querySelector('.content');
                        if (newContent) {
                            contentElement.innerHTML = newContent.innerHTML;
                            console.log('Template reloaded successfully!');
                            
                            // Khởi tạo lại các sự kiện cho các phần tử mới
                            initializeEvents();
                        }
                    }
                    
                    // Dừng hiệu ứng quay
                    this.classList.remove('refreshing');
                })
                .catch(error => {
                    console.error('Error reloading template:', error);
                    // Nếu có lỗi, thực hiện tải lại toàn bộ trang
                    location.reload();
                });
        });
    }

    // Sidebar toggle functionality
    const sidebarToggle = document.getElementById('sidebarToggle');
    const appContainer = document.querySelector('.app-container');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            appContainer.classList.toggle('sidebar-collapsed');
        });
    }

    // Responsive sidebar behavior
    function handleResize() {
        if (window.innerWidth <= 768) {
            appContainer.classList.add('sidebar-collapsed');
        } else {
            appContainer.classList.remove('sidebar-collapsed');
        }
    }

    // Initial call and add event listener
    handleResize();
    window.addEventListener('resize', handleResize);

    // Form validation
    const commandForm = document.querySelector('.command-form');
    if (commandForm) {
        commandForm.addEventListener('submit', function(e) {
            const commandTextarea = document.getElementById('command');
            if (!commandTextarea.value.trim()) {
                e.preventDefault();
                commandTextarea.classList.add('error');

                // Create error message if it doesn't exist
                let errorMsg = commandTextarea.nextElementSibling;
                if (!errorMsg || !errorMsg.classList.contains('error-message')) {
                    errorMsg = document.createElement('div');
                    errorMsg.classList.add('error-message');
                    errorMsg.textContent = 'Vui lòng nhập lệnh trước khi thực thi';
                    commandTextarea.parentNode.insertBefore(errorMsg, commandTextarea.nextSibling);
                }

                // Focus and remove error on input
                commandTextarea.focus();
                commandTextarea.addEventListener('input', function() {
                    if (this.value.trim()) {
                        this.classList.remove('error');
                        if (errorMsg) errorMsg.remove();
                    }
                }, { once: true });
            }
        });
    }

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.btn-icon[title="Sao chép"]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const resultContent = document.getElementById('result-content');
            if (resultContent && resultContent.textContent) {
                navigator.clipboard.writeText(resultContent.textContent)
                    .then(() => {
                        // Show copied notification
                        const notification = document.createElement('div');
                        notification.classList.add('toast-notification');
                        notification.textContent = 'Đã sao chép vào clipboard';
                        document.body.appendChild(notification);

                        // Remove notification after 2 seconds
                        setTimeout(() => {
                            notification.classList.add('fade-out');
                            setTimeout(() => {
                                notification.remove();
                            }, 300);
                        }, 2000);
                    })
                    .catch(err => {
                        console.error('Không thể sao chép: ', err);
                    });
            }
        });
    });

    // History item rerun functionality
    const rerunButtons = document.querySelectorAll('.history-actions .btn-icon[title="Chạy lại"]');
    rerunButtons.forEach(button => {
        button.addEventListener('click', function() {
            const historyItem = this.closest('.history-item');
            const command = historyItem.querySelector('.history-command').textContent;

            // Fill command in the form
            const commandTextarea = document.getElementById('command');
            if (commandTextarea) {
                commandTextarea.value = command;
                commandTextarea.focus();

                // Scroll to command form
                const commandCard = document.querySelector('.command-card');
                if (commandCard) {
                    commandCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });

    // Tooltip functionality
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltipText = this.getAttribute('title');
            this.setAttribute('data-title', tooltipText);
            this.removeAttribute('title');

            const tooltip = document.createElement('div');
            tooltip.classList.add('tooltip');
            tooltip.textContent = tooltipText;

            document.body.appendChild(tooltip);

            const rect = this.getBoundingClientRect();
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';

            this.addEventListener('mouseleave', function() {
                if (tooltip) {
                    document.body.removeChild(tooltip);
                }
                this.setAttribute('title', this.getAttribute('data-title'));
                this.removeAttribute('data-title');
            }, { once: true });
        });
    });

    // Add smooth scrolling for all anchors
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Khởi tạo các sự kiện cho các phần tử trong trang
    initializeEvents();
    
    // Add animations for elements when they come into view
    const animateOnScroll = function() {
        const elements = document.querySelectorAll('.stat-card, .command-card, .output-card, .history-card');

        elements.forEach(element => {
            const elementPosition = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;

            if (elementPosition < windowHeight - 50) {
                element.classList.add('animated');
            }
        });
    };

    // Initial call and add event listener
    animateOnScroll();
    window.addEventListener('scroll', animateOnScroll);

    // Add CSS for dynamic elements
    const style = document.createElement('style');
    style.textContent = `
        /* Thêm style cho nút làm mới trang */
        .refresh-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            background-color: var(--light-gray);
            color: var(--info);
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: all 0.2s ease;
            margin-right: var(--space-3);
        }
        
        .refresh-btn:hover {
            background-color: var(--info);
            color: var(--white);
            transform: rotate(180deg);
        }
        
        .refresh-btn i {
            font-size: 16px;
            transition: transform 0.3s ease;
        }
        
        .refreshing {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Fix for sidebar display */
        .sidebar-nav ul.flex {
            display: flex !important;
            flex-direction: column !important;
            width: 100% !important;
        }
        
        .sidebar-nav ul.flex li {
            display: block !important;
            width: 100% !important;
        }
        
        .sidebar-nav .flex.flex-col {
            flex-direction: column !important;
        }
        
        /* Đảm bảo các mục trong sidebar hiển thị đúng */
        .sidebar-nav li a {
            display: flex !important;
            width: 100% !important;
        }
        
        .error {
            border-color: var(--error) !important;
        }
        
        .error-message {
            color: var(--error);
            font-size: var(--font-size-sm);
            margin-top: var(--space-1);
        }
        
        .toast-notification {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: var(--black);
            color: var(--white);
            padding: var(--space-3) var(--space-4);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-md);
            z-index: 1000;
            opacity: 1;
            transition: opacity 0.3s ease;
        }
        
        .toast-notification.fade-out {
            opacity: 0;
        }
        
        .tooltip {
            position: fixed;
            background-color: var(--black);
            color: var(--white);
            padding: var(--space-2) var(--space-3);
            border-radius: var(--border-radius);
            font-size: var(--font-size-xs);
            z-index: 1000;
            pointer-events: none;
        }
        
        .tooltip:after {
            content: '';
            position: absolute;
            bottom: -6px;
            left: 50%;
            transform: translateX(-50%);
            border-width: 6px 6px 0;
            border-style: solid;
            border-color: var(--black) transparent transparent;
        }
        
        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
            }
        }
        
        .pulse {
            animation: pulse 1.5s ease-out;
        }
        
        .animated {
            animation: fadeInUp 0.5s ease-out forwards;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;

    document.head.appendChild(style);
});