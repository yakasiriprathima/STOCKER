// Global variables
let currentSection = 'home';
let stockUpdateInterval;

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize navigation
    initializeNavigation();
    
    // Initialize forms
    initializeForms();
    
    // Initialize stock updates if on dashboard
    if (window.location.pathname.includes('dashboard')) {
        initializeStockUpdates();
    }
    
    // Initialize trade form if on trade page
    if (window.location.pathname.includes('trade')) {
        initializeTradeForm();
    }
    
    // Initialize portfolio if on portfolio page
    if (window.location.pathname.includes('portfolio')) {
        initializePortfolio();
    }
}

// Navigation functions
function initializeNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.addEventListener('click', handleNavigation);
    });
}

function handleNavigation(e) {
    e.preventDefault();
    const targetSection = e.target.getAttribute('onclick');
    if (targetSection) {
        const sectionName = targetSection.match(/showSection\('(.+)'\)/)[1];
        showSection(sectionName);
    }
}

function showSection(sectionName) {
    // Hide all sections
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => {
        section.classList.remove('active');
    });
    
    // Show target section
    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // Update nav buttons
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase() === sectionName) {
            btn.classList.add('active');
        }
    });
    
    currentSection = sectionName;
}

// Form functions
function initializeForms() {
    // Initialize signup form
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        initializeSignupForm();
    }
    
    // Initialize login form
    const loginForm = document.querySelector('.auth-form');
    if (loginForm && window.location.pathname.includes('login')) {
        initializeLoginForm();
    }
}

function initializeSignupForm() {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const submitBtn = document.getElementById('submitBtn');
    
    if (usernameInput) {
        usernameInput.addEventListener('input', debounce(checkUsername, 500));
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('input', validatePassword);
    }
    
    if (submitBtn) {
        const form = document.getElementById('signupForm');
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
            }
        });
    }
}

function initializeLoginForm() {
    const form = document.querySelector('.auth-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const role = document.getElementById('role').value;
            
            if (!username || !password || !role) {
                e.preventDefault();
                alert('Please fill in all fields');
            }
        });
    }
}

function checkUsername() {
    const username = document.getElementById('username').value;
    const statusDiv = document.getElementById('usernameStatus');
    
    if (!username) {
        statusDiv.textContent = '';
        return;
    }
    
    fetch(`/check_username?username=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            if (data.exists) {
                statusDiv.textContent = 'Username is already taken';
                statusDiv.className = 'username-status taken';
            } else {
                statusDiv.textContent = 'Username is available';
                statusDiv.className = 'username-status available';
            }
        })
        .catch(error => {
            console.error('Error checking username:', error);
            statusDiv.textContent = '';
        });
}

function validatePassword() {
    const password = document.getElementById('password').value;
    const lengthReq = document.getElementById('length');
    const specialReq = document.getElementById('special');
    const numberReq = document.getElementById('number');
    
    if (!lengthReq || !specialReq || !numberReq) return;
    
    // Check length
    if (password.length >= 8) {
        lengthReq.classList.add('valid');
    } else {
        lengthReq.classList.remove('valid');
    }
    
    // Check special character
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
        specialReq.classList.add('valid');
    } else {
        specialReq.classList.remove('valid');
    }
    
    // Check number
    if (/\d/.test(password)) {
        numberReq.classList.add('valid');
    } else {
        numberReq.classList.remove('valid');
    }
}

function validateForm() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const email = document.getElementById('email').value;
    const usernameStatus = document.getElementById('usernameStatus');
    
    // Check if username is available
    if (usernameStatus.classList.contains('taken')) {
        alert('Please choose a different username');
        return false;
    }
    
    // Check password requirements
    if (password.length < 8) {
        alert('Password must be at least 8 characters long');
        return false;
    }
    
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
        alert('Password must contain at least one special character');
        return false;
    }
    
    if (!/\d/.test(password)) {
        alert('Password must contain at least one number');
        return false;
    }
    
    return true;
}

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const button = input.nextElementSibling;
    
    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = '🙈';
    } else {
        input.type = 'password';
        button.textContent = '👁️';
    }
}

// Stock functions
function initializeStockUpdates() {
    loadStockPrices();
    stockUpdateInterval = setInterval(loadStockPrices, 10000); // Update every 10 seconds
}

function loadStockPrices() {
    fetch('/get_stock_prices')
        .then(response => response.json())
        .then(data => {
            updateStockGrid(data);
            updateLastUpdateTime();
        })
        .catch(error => {
            console.error('Error loading stock prices:', error);
        });
}

function updateStockGrid(stocksData) {
    const stocksGrid = document.getElementById('stocksGrid');
    if (!stocksGrid) return;
    
    stocksGrid.innerHTML = '';
    
    for (const [symbol, data] of Object.entries(stocksData)) {
        const stockCard = createStockCard(symbol, data);
        stocksGrid.appendChild(stockCard);
    }
}

function createStockCard(symbol, data) {
    const card = document.createElement('div');
    card.className = 'stock-card';
    
    const isTraderDashboard = window.location.pathname.includes('dashboard') && 
                             !window.location.pathname.includes('admin');
    
    card.innerHTML = `
        <div class="stock-header">
            <div class="stock-symbol">${symbol}</div>
            <div class="stock-price">$${data.price.toFixed(2)}</div>
        </div>
        <div class="stock-name">${data.name}</div>
        ${isTraderDashboard ? `
            <div class="stock-actions">
                <button class="btn btn-small btn-buy" onclick="goToTrade('${symbol}', 'Buy')">Buy</button>
                <button class="btn btn-small btn-sell" onclick="goToTrade('${symbol}', 'Sell')">Sell</button>
            </div>
        ` : ''}
    `;
    
    return card;
}

function goToTrade(symbol, action) {
    const url = new URL('/trade', window.location.origin);
    url.searchParams.set('symbol', symbol);
    url.searchParams.set('action', action);
    window.location.href = url.toString();
}

function updateLastUpdateTime() {
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        const now = new Date();
        lastUpdateElement.textContent = now.toLocaleTimeString();
    }
}

// Trade functions
function initializeTradeForm() {
    const symbolSelect = document.getElementById('symbol');
    const quantityInput = document.getElementById('quantity');
    const priceInput = document.getElementById('price');
    
    if (symbolSelect) {
        symbolSelect.addEventListener('change', updatePrice);
    }
    
    if (quantityInput) {
        quantityInput.addEventListener('input', calculateTotal);
    }
    
    if (priceInput) {
        priceInput.addEventListener('input', calculateTotal);
    }
    
    // Check URL parameters for pre-selected stock
    const urlParams = new URLSearchParams(window.location.search);
    const preSelectedSymbol = urlParams.get('symbol');
    const preSelectedAction = urlParams.get('action');
    
    if (preSelectedSymbol && symbolSelect) {
        symbolSelect.value = preSelectedSymbol;
        updatePrice();
    }
    
    if (preSelectedAction) {
        const actionSelect = document.getElementById('action');
        if (actionSelect) {
            actionSelect.value = preSelectedAction;
        }
    }
}

function updatePrice() {
    const symbol = document.getElementById('symbol').value;
    const priceInput = document.getElementById('price');
    
    if (!symbol || !priceInput) {
        if (priceInput) priceInput.value = '';
        calculateTotal();
        return;
    }
    
    fetch('/get_stock_prices')
        .then(response => response.json())
        .then(data => {
            if (data[symbol]) {
                priceInput.value = data[symbol].price.toFixed(2);
                calculateTotal();
            } else {
                priceInput.value = '';
                calculateTotal();
            }
        })
        .catch(error => {
            console.error('Error updating price:', error);
            priceInput.value = '';
            calculateTotal();
        });
}

function calculateTotal() {
    const quantityInput = document.getElementById('quantity');
    const priceInput = document.getElementById('price');
    const totalInput = document.getElementById('total');
    
    if (!quantityInput || !priceInput || !totalInput) return;
    
    const quantity = quantityInput.value;
    const price = priceInput.value;
    
    if (!quantity || !price || quantity <= 0 || price <= 0) {
        totalInput.value = '';
        return;
    }
    
    const total = (parseFloat(quantity) * parseFloat(price)).toFixed(2);
    totalInput.value = `$${total}`;
}

// Portfolio functions
function initializePortfolio() {
    updatePortfolioPrices();
    setInterval(updatePortfolioPrices, 10000); // Update every 10 seconds
}

function updatePortfolioPrices() {
    const currentPriceCells = document.querySelectorAll('[data-symbol]');
    if (currentPriceCells.length === 0) return;
    
    fetch('/get_stock_prices')
        .then(response => response.json())
        .then(stocksData => {
            let totalValue = 0;
            let totalGainLoss = 0;
            
            currentPriceCells.forEach(cell => {
                const symbol = cell.getAttribute('data-symbol');
                const currentPrice = stocksData[symbol].price;
                
                // Update current price
                cell.textContent = `$${currentPrice.toFixed(2)}`;
                
                // Find row and update calculations
                const row = cell.closest('tr');
                if (row) {
                    const quantityCell = row.cells[2];
                    const avgPriceCell = row.cells[3];
                    const totalValueCell = row.cells[5];
                    const gainLossCell = row.cells[6];
                    
                    if (quantityCell && avgPriceCell && totalValueCell && gainLossCell) {
                        const quantity = parseInt(quantityCell.textContent);
                        const avgPrice = parseFloat(avgPriceCell.textContent.replace('$', ''));
                        const currentValue = quantity * currentPrice;
                        const gainLoss = currentValue - (quantity * avgPrice);
                        
                        totalValue += currentValue;
                        totalGainLoss += gainLoss;
                        
                        // Update total value
                        totalValueCell.textContent = `$${currentValue.toFixed(2)}`;
                        
                        // Update gain/loss
                        if (gainLoss >= 0) {
                            gainLossCell.innerHTML = `<span class="positive">+$${gainLoss.toFixed(2)}</span>`;
                        } else {
                            gainLossCell.innerHTML = `<span class="negative">-$${Math.abs(gainLoss).toFixed(2)}</span>`;
                        }
                    }
                }
            });
            
            // Update summary
            const totalValueElement = document.getElementById('totalValue');
            const totalGainLossElement = document.getElementById('totalGainLoss');
            
            if (totalValueElement) {
                totalValueElement.textContent = `$${totalValue.toFixed(2)}`;
            }
            
            if (totalGainLossElement) {
                if (totalGainLoss >= 0) {
                    totalGainLossElement.innerHTML = `<span class="positive">+$${totalGainLoss.toFixed(2)}</span>`;
                } else {
                    totalGainLossElement.innerHTML = `<span class="negative">-$${Math.abs(totalGainLoss).toFixed(2)}</span>`;
                }
            }
        })
        .catch(error => {
            console.error('Error updating portfolio prices:', error);
        });
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatNumber(number) {
    return new Intl.NumberFormat('en-US').format(number);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Error handling
function handleError(error, context = 'Operation') {
    console.error(`${context} failed:`, error);
    
    // Show user-friendly error message
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-error';
    alertDiv.innerHTML = `<p>${context} failed. Please try again.</p>`;
    
    const mainContent = document.querySelector('.main-content') || document.body;
    mainContent.insertBefore(alertDiv, mainContent.firstChild);
    
    // Remove error message after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Cleanup function
function cleanup() {
    if (stockUpdateInterval) {
        clearInterval(stockUpdateInterval);
    }
}

// Handle page unload
window.addEventListener('beforeunload', cleanup);

// Handle visibility change (pause updates when tab is not visible)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        cleanup();
    } else {
        if (window.location.pathname.includes('dashboard')) {
            initializeStockUpdates();
        }
    }
});