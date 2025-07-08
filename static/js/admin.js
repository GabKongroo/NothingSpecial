// Toast System
class ToastManager {
  constructor() {
    this.container = document.getElementById('toast-container');
    this.toasts = new Map();
    this.toastId = 0;
  }

  show(message, type = 'info', options = {}) {
    const id = ++this.toastId;
    const toast = this.createToast(id, message, type, options);
    
    this.container.appendChild(toast);
    this.toasts.set(id, toast);

    // Auto remove after duration
    const duration = options.duration || (type === 'error' ? 6000 : 4000);
    setTimeout(() => this.remove(id), duration);

    // Animate in
    requestAnimationFrame(() => {
      toast.style.transform = 'translateX(0)';
      toast.style.opacity = '1';
    });

    return id;
  }

  createToast(id, message, type, options) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.style.transform = 'translateX(100%)';
    toast.style.opacity = '0';
    toast.style.transition = 'all 0.3s ease-out';

    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };

    toast.innerHTML = `
      <div class="toast-content">
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-message">
          ${options.title ? `<div class="toast-title">${options.title}</div>` : ''}
          <div class="toast-description">${message}</div>
        </div>
      </div>
      <button class="toast-close" onclick="toastManager.remove(${id})">&times;</button>
    `;

    return toast;
  }

  remove(id) {
    const toast = this.toasts.get(id);
    if (!toast) return;

    toast.style.animation = 'slideOutRight 0.3s ease-in forwards';
    
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
      this.toasts.delete(id);
    }, 300);
  }

  clear() {
    this.toasts.forEach((toast, id) => this.remove(id));
  }
}

// Initialize toast manager
const toastManager = new ToastManager();

// Custom Modal System (iOS-friendly replacement for confirm/alert)
class ModalManager {
  constructor() {
    this.modalId = 0;
    this.activeModals = new Map();
    this.init();
  }

  init() {
    // Create modal container if it doesn't exist
    if (!document.getElementById('modal-container')) {
      const container = document.createElement('div');
      container.id = 'modal-container';
      document.body.appendChild(container);
    }
  }

  async confirm(title, message, options = {}) {
    return new Promise((resolve) => {
      const id = ++this.modalId;
      const modal = this.createModal(id, title, message, 'confirm', options);
      
      const container = document.getElementById('modal-container');
      container.appendChild(modal);
      
      this.activeModals.set(id, { modal, resolve });
      
      // Show modal
      requestAnimationFrame(() => {
        modal.classList.add('active');
      });
    });
  }

  async alert(title, message, options = {}) {
    return new Promise((resolve) => {
      const id = ++this.modalId;
      const modal = this.createModal(id, title, message, 'alert', options);
      
      const container = document.getElementById('modal-container');
      container.appendChild(modal);
      
      this.activeModals.set(id, { modal, resolve });
      
      // Show modal
      requestAnimationFrame(() => {
        modal.classList.add('active');
      });
    });
  }

  createModal(id, title, message, type, options = {}) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = `modal-${id}`;

    const iconMap = {
      confirm: '❓',
      alert: '⚠️',
      error: '❌',
      info: 'ℹ️',
      warning: '⚠️'
    };

    const iconClass = options.type || (type === 'confirm' ? 'warning' : 'info');
    const icon = options.icon || iconMap[type] || iconMap.info;

    const confirmText = options.confirmText || 'Conferma';
    const cancelText = options.cancelText || 'Annulla';

    let actions = '';
    if (type === 'confirm') {
      actions = `
        <div class="modal-actions">
          <button class="modal-btn secondary" onclick="modalManager.close(${id}, false)">
            ${cancelText}
          </button>
          <button class="modal-btn danger" onclick="modalManager.close(${id}, true)">
            ${confirmText}
          </button>
        </div>
      `;
    } else {
      actions = `
        <div class="modal-actions">
          <button class="modal-btn primary" onclick="modalManager.close(${id}, true)">
            OK
          </button>
        </div>
      `;
    }

    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <div class="modal-icon ${iconClass}">${icon}</div>
          <div class="modal-title">${title}</div>
        </div>
        <div class="modal-message">${message}</div>
        ${actions}
      </div>
    `;

    // Close on backdrop click
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        this.close(id, false);
      }
    });

    // Handle keyboard events
    const handleKeydown = (e) => {
      if (e.key === 'Escape') {
        this.close(id, false);
      } else if (e.key === 'Enter' && type === 'alert') {
        this.close(id, true);
      }
    };

    overlay.addEventListener('keydown', handleKeydown);

    return overlay;
  }

  close(id, result) {
    const modalData = this.activeModals.get(id);
    if (modalData) {
      const { modal, resolve } = modalData;
      
      // Animate out
      modal.classList.remove('active');
      
      // Remove from DOM after animation
      setTimeout(() => {
        if (modal.parentNode) {
          modal.parentNode.removeChild(modal);
        }
        resolve(result);
      }, 300);
      
      this.activeModals.delete(id);
    }
  }

  // Convenience methods
  async showError(message, title = 'Errore') {
    return this.alert(title, message, { type: 'error', icon: '❌' });
  }

  async showSuccess(message, title = 'Successo') {
    return this.alert(title, message, { type: 'success', icon: '✅' });
  }

  async showWarning(message, title = 'Attenzione') {
    return this.alert(title, message, { type: 'warning', icon: '⚠️' });
  }

  async showInfo(message, title = 'Informazione') {
    return this.alert(title, message, { type: 'info', icon: 'ℹ️' });
  }
}

const modalManager = new ModalManager();

// Global helper functions to replace native alert/confirm
window.showAlert = (message, title = 'Attenzione') => modalManager.alert(title, message);
window.showConfirm = (message, title = 'Conferma') => modalManager.confirm(title, message);
window.showError = (message, title = 'Errore') => modalManager.showError(message, title);
window.showSuccess = (message, title = 'Successo') => modalManager.showSuccess(message, title);
window.showWarning = (message, title = 'Attenzione') => modalManager.showWarning(message, title);
window.showInfo = (message, title = 'Informazione') => modalManager.showInfo(message, title);

// Enhanced error handling with better UX
class ErrorHandler {
  constructor() {
    this.activeErrors = new Map();
  }

  showError(beatId, message, options = {}) {
    // Clear any existing error for this beat
    this.clearError(beatId);

    // Show toast notification
    const toastId = toastManager.show(message, 'error', {
      title: 'Errore di Validazione',
      duration: 6000
    });

    // Show inline error if beat card exists
    const errorContainer = document.getElementById(`error-container-${beatId}`);
    if (errorContainer) {
      const errorMessage = errorContainer.querySelector('.error-message');
      if (errorMessage) {
        errorMessage.textContent = message;
        errorContainer.style.display = 'block';
        
        // Animate in
        errorContainer.style.animation = 'slideDown 0.3s ease-out';
      }
    }

    // Scroll to beat and highlight it
    this.scrollToBeat(beatId);

    // Store error reference
    this.activeErrors.set(beatId, { toastId, message });

    // Auto-clear error after delay
    setTimeout(() => this.clearError(beatId), 8000);
  }

  clearError(beatId) {
    const error = this.activeErrors.get(beatId);
    if (error) {
      // Remove toast
      toastManager.remove(error.toastId);
      
      // Hide inline error
      const errorContainer = document.getElementById(`error-container-${beatId}`);
      if (errorContainer) {
        errorContainer.style.display = 'none';
      }
      
      this.activeErrors.delete(beatId);
    }
  }

  scrollToBeat(beatId) {
    const beatCard = document.getElementById(`beat-card-${beatId}`);
    if (beatCard) {
      // Smooth scroll to beat
      beatCard.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });

      // Add highlight effect
      beatCard.classList.add('error-highlight');
      
      // Remove highlight after animation
      setTimeout(() => {
        beatCard.classList.remove('error-highlight');
      }, 2000);
    }
  }

  showSuccess(message, options = {}) {
    toastManager.show(message, 'success', {
      title: 'Operazione Completata',
      ...options
    });
  }
}

// Initialize error handler
const errorHandler = new ErrorHandler();

// Loading state management
class LoadingManager {
  constructor() {
    this.loadingStates = new Map();
    this.overlay = document.getElementById('loading-overlay');
  }

  showButtonLoading(buttonElement) {
    if (!buttonElement) return;
    
    const btnText = buttonElement.querySelector('.btn-text');
    const btnIcon = buttonElement.querySelector('.btn-icon');
    const btnLoading = buttonElement.querySelector('.btn-loading');
    
    if (btnText) btnText.style.opacity = '0';
    if (btnIcon) btnIcon.style.opacity = '0';
    if (btnLoading) btnLoading.style.display = 'block';
    
    buttonElement.disabled = true;
    buttonElement.classList.add('loading');
  }

  hideButtonLoading(buttonElement) {
    if (!buttonElement) return;
    
    const btnText = buttonElement.querySelector('.btn-text');
    const btnIcon = buttonElement.querySelector('.btn-icon');
    const btnLoading = buttonElement.querySelector('.btn-loading');
    
    if (btnText) btnText.style.opacity = '1';
    if (btnIcon) btnIcon.style.opacity = '1';
    if (btnLoading) btnLoading.style.display = 'none';
    
    buttonElement.disabled = false;
    buttonElement.classList.remove('loading');
  }

  showOverlay() {
    if (this.overlay) {
      this.overlay.classList.add('active');
    }
  }

  hideOverlay() {
    if (this.overlay) {
      this.overlay.classList.remove('active');
    }
  }
}

// Initialize loading manager
const loadingManager = new LoadingManager();

// Enhanced validation with better user feedback
class BeatValidator {
  constructor() {
    this.rules = {
      originalPrice: {
        required: true,
        min: 0.01,
        message: 'Il prezzo originale deve essere maggiore di 0'
      },
      discountedPrice: {
        min: 0.01,
        message: 'Il prezzo scontato deve essere maggiore di 0'
      },
      discountPercent: {
        min: 1,
        max: 99,
        message: 'La percentuale di sconto deve essere tra 1 e 99'
      }
    };
  }

  validateBeat(beatData) {
    const errors = [];

    // Validate original price
    if (!beatData.original_price || beatData.original_price <= 0) {
      errors.push('Il prezzo originale deve essere maggiore di 0');
    }

    // Validate discount logic
    if (beatData.is_discounted) {
      if (!beatData.discounted_price || beatData.discounted_price <= 0) {
        errors.push('Il prezzo scontato deve essere maggiore di 0');
      }
      
      if (beatData.discounted_price >= beatData.original_price) {
        errors.push('Il prezzo scontato deve essere minore del prezzo originale');
      }
      
      if (!beatData.discount_percent || beatData.discount_percent <= 0 || beatData.discount_percent > 99) {
        errors.push('La percentuale di sconto deve essere tra 1 e 99');
      }
    }

    return errors;
  }

  validateField(fieldName, value, beatData) {
    switch (fieldName) {
      case 'originalPrice':
        if (!value || value <= 0) {
          return 'Il prezzo originale deve essere maggiore di 0';
        }
        break;
      
      case 'discountedPrice':
        if (beatData.isDiscounted) {
          if (!value || value <= 0) {
            return 'Il prezzo scontato deve essere maggiore di 0';
          }
          if (value >= beatData.originalPrice) {
            return 'Il prezzo scontato deve essere minore del prezzo originale';
          }
        }
        break;
      
      case 'discountPercent':
        if (beatData.isDiscounted) {
          if (!value || value <= 0 || value > 99) {
            return 'La percentuale di sconto deve essere tra 1 e 99';
          }
        }
        break;
    }
    return null;
  }
}

// Initialize validator
const validator = new BeatValidator();

// Enhanced beat management with mobile support and position preservation
class BeatManager {
  constructor() {
    this.beats = new Map();
    this.initializeEventListeners();
    this.loadBeatsFromDOM();
    this.initializeMobileControls();
    this.initializeScrollToSaved();
  }

  loadBeatsFromDOM() {
    // Load existing beat data from form inputs
    document.querySelectorAll('.beat-card').forEach(card => {
      const beatId = parseInt(card.dataset.beatId);
      if (beatId) {
        this.beats.set(beatId, this.getBeatDataFromDOM(beatId));
      }
    });
  }

  getBeatDataFromDOM(beatId) {
    return {
      id: beatId,
      originalPrice: parseFloat(document.querySelector(`input.original-price[data-id='${beatId}']`)?.value) || 0,
      discountedPrice: parseFloat(document.querySelector(`input.discounted-price[data-id='${beatId}']`)?.value) || 0,
      discountPercent: parseInt(document.querySelector(`input.discount-percent[data-id='${beatId}']`)?.value) || 0,
      isDiscounted: document.querySelector(`input.is-discounted[data-id='${beatId}']`)?.checked || false,
      isExclusive: document.querySelector(`input[name='is_exclusive_${beatId}']`)?.checked || false
    };
  }

  updateBeat(beatId, field, value) {
    const beat = this.beats.get(beatId) || {};
    beat[field] = value;
    this.beats.set(beatId, beat);

    // Auto-calculate discounted price
    if (field === 'originalPrice' || field === 'discountPercent') {
      this.autoCalculateDiscountedPrice(beatId);
    }

    // Clear any existing errors for this beat
    errorHandler.clearError(beatId);
  }

  autoCalculateDiscountedPrice(beatId) {
    const beat = this.beats.get(beatId);
    if (!beat || !beat.isDiscounted) return;

    const originalInput = document.querySelector(`input.original-price[data-id='${beatId}']`);
    const discountPercentInput = document.querySelector(`input.discount-percent[data-id='${beatId}']`);
    const discountedInput = document.querySelector(`input.discounted-price[data-id='${beatId}']`);

    const original = parseFloat(originalInput?.value) || 0;
    const discountPercent = parseInt(discountPercentInput?.value) || 0;

    if (original > 0 && discountPercent > 0) {
      const discountedPrice = original * (1 - discountPercent / 100);
      const roundedPrice = Math.round(discountedPrice * 100) / 100;
      
      if (discountedInput) {
        discountedInput.value = roundedPrice.toFixed(2);
        beat.discountedPrice = roundedPrice;
        this.beats.set(beatId, beat);
      }
    }
  }

  async saveBeat(beatId) {
    const beat = this.getBeatDataFromDOM(beatId);
    const errors = validator.validateBeat(beat);

    if (errors.length > 0) {
      errorHandler.showError(beatId, errors[0]);
      return false;
    }

    const button = document.querySelector(`button[data-beat-id='${beatId}']`);
    loadingManager.showButtonLoading(button);

    try {
      // Create form data for single beat save
      const formData = new FormData();
      formData.append(`original_price_${beatId}`, beat.originalPrice);
      formData.append(`discounted_price_${beatId}`, beat.discountedPrice || '');
      formData.append(`is_exclusive_${beatId}`, beat.isExclusive ? '1' : '0');
      formData.append(`is_discounted_${beatId}`, beat.isDiscounted ? '1' : '0');
      formData.append(`discount_percent_${beatId}`, beat.discountPercent);

      const response = await fetch(window.location.pathname, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        // Redirect with scroll parameter to maintain position
        const url = new URL(window.location);
        url.searchParams.set('scroll_to_beat', beatId);
        window.location.href = url.toString();
        return true;
      } else {
        throw new Error('Errore durante il salvataggio');
      }
    } catch (error) {
      errorHandler.showError(beatId, 'Errore durante il salvataggio. Riprova.');
      return false;
    } finally {
      loadingManager.hideButtonLoading(button);
    }
  }

  initializeMobileControls() {
    // Only add mobile controls if we're on mobile
    if (window.innerWidth <= 768) {
      this.addMobileControls();
    }
    
    // Handle window resize
    window.addEventListener('resize', () => {
      if (window.innerWidth <= 768 && !document.querySelector('.mobile-controls')) {
        this.addMobileControls();
      } else if (window.innerWidth > 768) {
        this.removeMobileControls();
      }
    });
  }

  addMobileControls() {
    if (document.querySelector('.mobile-controls')) return;
    
    const mobileControls = document.createElement('div');
    mobileControls.className = 'mobile-controls';
    mobileControls.innerHTML = `
      <div class="mobile-nav-controls">
        <button class="mobile-nav-btn" onclick="beatManager.scrollToTop()" title="Vai all'inizio">
          ⬆️
        </button>
        <button class="mobile-nav-btn" onclick="beatManager.scrollToBottom()" title="Vai alla fine">
          ⬇️
        </button>
      </div>
      <button class="mobile-save-all" onclick="beatManager.saveAllBeats()" title="Salva tutti">
        <span class="btn-icon">💾</span>
        <div class="btn-loading" style="display: none;">
          <div class="btn-spinner"></div>
        </div>
      </button>
    `;
    
    document.body.appendChild(mobileControls);
  }

  removeMobileControls() {
    const controls = document.querySelector('.mobile-controls');
    if (controls) {
      controls.remove();
    }
  }

  scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  scrollToBottom() {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  }

  initializeScrollToSaved() {
    // Check if we should scroll to a specific beat after page load
    const urlParams = new URLSearchParams(window.location.search);
    const scrollToBeat = urlParams.get('scroll_to_beat');
    
    if (scrollToBeat) {
      setTimeout(() => {
        const beatCard = document.getElementById(`beat-card-${scrollToBeat}`);
        if (beatCard) {
          beatCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
          beatCard.classList.add('saving-highlight');
          
          // Remove highlight after animation
          setTimeout(() => {
            beatCard.classList.remove('saving-highlight');
          }, 1000);
        }
      }, 100);
    }
  }

  async saveBeat(beatId) {
    const beat = this.getBeatDataFromDOM(beatId);
    const errors = validator.validateBeat(beat);

    if (errors.length > 0) {
      errorHandler.showError(beatId, errors[0]);
      return false;
    }

    const button = document.querySelector(`button[data-beat-id='${beatId}']`);
    loadingManager.showButtonLoading(button);

    try {
      // Create form data for single beat save
      const formData = new FormData();
      formData.append(`original_price_${beatId}`, beat.originalPrice);
      formData.append(`discounted_price_${beatId}`, beat.discountedPrice || '');
      formData.append(`is_exclusive_${beatId}`, beat.isExclusive ? '1' : '0');
      formData.append(`is_discounted_${beatId}`, beat.isDiscounted ? '1' : '0');
      formData.append(`discount_percent_${beatId}`, beat.discountPercent);

      const response = await fetch(window.location.pathname, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        // Redirect with scroll parameter to maintain position
        const url = new URL(window.location);
        url.searchParams.set('scroll_to_beat', beatId);
        window.location.href = url.toString();
        return true;
      } else {
        throw new Error('Errore durante il salvataggio');
      }
    } catch (error) {
      errorHandler.showError(beatId, 'Errore durante il salvataggio. Riprova.');
      return false;
    } finally {
      loadingManager.hideButtonLoading(button);
    }
  }

  async saveAllBeats() {
    console.log('🔄 saveAllBeats() chiamata'); // Debug
    
    // Check if we're on the right page
    const beatCards = document.querySelectorAll('.beat-card');
    if (beatCards.length === 0) {
      console.warn('⚠️ No beat cards found on this page');
      toastManager.show('Nessun beat trovato per il salvataggio', 'warning', {
        title: 'Nessun Beat'
      });
      return;
    }
    
    console.log(`📊 Found ${beatCards.length} beat cards`); // Debug
    
    // Raccolta dati LIVE dal DOM invece che dalla cache
    const allBeats = [];
    document.querySelectorAll('.beat-card').forEach(card => {
      const beatId = parseInt(card.dataset.beatId);
      if (!beatId) return;
      
      const originalPriceInput = card.querySelector(`input[name='original_price_${beatId}']`);
      const discountedPriceInput = card.querySelector(`input[name='discounted_price_${beatId}']`);
      const isExclusiveInput = card.querySelector(`input[name='is_exclusive_${beatId}']:checked`);
      const isDiscountedInput = card.querySelector(`input[name='is_discounted_${beatId}']:checked`);
      const discountPercentInput = card.querySelector(`input[name='discount_percent_${beatId}']`);
      
      const beatData = {
        id: beatId,
        original_price: parseFloat(originalPriceInput?.value) || 0,
        discounted_price: parseFloat(discountedPriceInput?.value) || 0,
        is_exclusive: isExclusiveInput ? 1 : 0,
        is_discounted: isDiscountedInput ? 1 : 0,
        discount_percent: parseInt(discountPercentInput?.value) || 0
      };
      
      console.log(`Beat ${beatId} data:`, beatData); // Debug
      allBeats.push(beatData);
    });
    
    console.log('📊 Dati raccolti:', allBeats); // Debug

    // Debug validazione
    console.log('🔍 Inizio validazione beat...');
    let hasErrors = false;
    let errorMessages = [];
    
    allBeats.forEach((beat, index) => {
      const errors = validator.validateBeat(beat);
      if (errors.length > 0) {
        console.error(`❌ Errori validazione beat ${beat.id}:`, errors);
        console.error(`Beat data:`, beat);
        hasErrors = true;
        errorMessages = errorMessages.concat(errors);
      } else {
        console.log(`✅ Beat ${beat.id} validato correttamente`);
      }
    });

    if (hasErrors) {
      console.error('❌ Validazione fallita. Errori trovati:', errorMessages);
      toastManager.show('Correggi tutti gli errori prima di salvare: ' + errorMessages.join(', '), 'error', {
        title: 'Validazione Fallita',
        duration: 8000
      });
      return false;
    }

    // Handle both desktop and mobile save buttons
    const desktopButton = document.getElementById('save-all-btn');
    const mobileButton = document.getElementById('mobile-save-all-btn');
    
    if (desktopButton) loadingManager.showButtonLoading(desktopButton);
    if (mobileButton) loadingManager.showButtonLoading(mobileButton);
    
    loadingManager.showOverlay();

    try {
      console.log('📡 Invio dati al server...'); // Debug
      
      // Send data to server
      const response = await fetch('/api/save-all-beats', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ beats: allBeats })
      });

      console.log('📨 Risposta server status:', response.status); // Debug
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('📊 Risultato server:', result); // Debug

      if (result.success) {
        toastManager.show(result.message || 'Tutti i beat sono stati salvati con successo!', 'success', {
          title: 'Salvataggio Completato'
        });
        
        // Reload the page to show updated data
        setTimeout(() => {
          window.location.reload();
        }, 1500);
        
        return true;
      } else {
        toastManager.show(result.error || 'Errore durante il salvataggio', 'error', {
          title: 'Errore di Salvataggio'
        });
        
        // Show detailed errors if available
        if (result.details && Array.isArray(result.details)) {
          result.details.forEach(detail => {
            toastManager.show(detail, 'error', { duration: 8000 });
          });
        }
        
        return false;
      }
    } catch (error) {
      console.error('❌ Errore durante il salvataggio:', error);
      toastManager.show('Errore di connessione. Verifica la tua connessione internet e riprova.', 'error', {
        title: 'Errore di Rete'
      });
      return false;
    } finally {
      if (desktopButton) loadingManager.hideButtonLoading(desktopButton);
      if (mobileButton) loadingManager.hideButtonLoading(mobileButton);
      loadingManager.hideOverlay();
    }
  }

  initializeEventListeners() {
    // Original price changes
    document.addEventListener('input', (e) => {
      if (e.target.classList.contains('original-price')) {
        const beatId = parseInt(e.target.dataset.id);
        this.updateBeat(beatId, 'originalPrice', parseFloat(e.target.value) || 0);
      }
    });

    // Discount percent changes
    document.addEventListener('input', (e) => {
      if (e.target.classList.contains('discount-percent')) {
        const beatId = parseInt(e.target.dataset.id);
        this.updateBeat(beatId, 'discountPercent', parseInt(e.target.value) || 0);
      }
    });

    // Discounted price changes
    document.addEventListener('input', (e) => {
      if (e.target.classList.contains('discounted-price')) {
        const beatId = parseInt(e.target.dataset.id);
        const beat = this.getBeatDataFromDOM(beatId);
        
        if (!beat.isDiscounted && e.target.value) {
          errorHandler.showError(beatId, "Spunta 'Scontato' prima di inserire un prezzo scontato");
          e.target.value = '';
          return;
        }
        
        this.updateBeat(beatId, 'discountedPrice', parseFloat(e.target.value) || 0);
      }
    });

    // Discount checkbox changes
    document.addEventListener('change', (e) => {
      if (e.target.classList.contains('is-discounted')) {
        const beatId = parseInt(e.target.dataset.id);
        const isDiscounted = e.target.checked;
        
        this.updateBeat(beatId, 'isDiscounted', isDiscounted);
        
        if (!isDiscounted) {
          // Clear discount fields
          const discountedInput = document.querySelector(`input.discounted-price[data-id='${beatId}']`);
          const discountPercentInput = document.querySelector(`input.discount-percent[data-id='${beatId}']`);
          
          if (discountedInput) discountedInput.value = '';
          if (discountPercentInput) discountPercentInput.value = '0';
          
          this.updateBeat(beatId, 'discountedPrice', 0);
          this.updateBeat(beatId, 'discountPercent', 0);
        }
      }
    });
  }
}

// Image upload handler for bundles
class ImageUploadManager {
  constructor() {
    this.isUploading = false;
    this.initializeUploadHandlers();
  }

  initializeUploadHandlers() {
    const uploadArea = document.getElementById('image-upload-area');
    const fileInput = document.getElementById('bundle-image-input');
    
    if (!uploadArea || !fileInput) return;

    // Click to upload
    uploadArea.addEventListener('click', () => {
      if (!this.isUploading) {
        fileInput.click();
      }
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      if (!this.isUploading) {
        uploadArea.classList.add('dragover');
      }
    });

    uploadArea.addEventListener('dragleave', () => {
      if (!this.isUploading) {
        uploadArea.classList.remove('dragover');
      }
    });

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      
      if (!this.isUploading && e.dataTransfer.files.length > 0) {
        this.handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
      if (!this.isUploading && e.target.files.length > 0) {
        this.handleFileUpload(e.target.files[0]);
      }
    });
  }

  async handleFileUpload(file) {
    // Prevent multiple uploads
    if (this.isUploading) {
      console.log('Upload already in progress, ignoring...');
      return;
    }

    if (!file.type.startsWith('image/')) {
      toastManager.show('Per favore seleziona un file immagine valido', 'error');
      return;
    }

    if (file.size > 5 * 1024 * 1024) { // 5MB limit
      toastManager.show('Il file è troppo grande. Massimo 5MB consentiti.', 'error');
      return;
    }

    this.isUploading = true;
    const uploadArea = document.getElementById('image-upload-area');
    const fileInput = document.getElementById('bundle-image-input');
    
    try {
      // Show loading state
      uploadArea.innerHTML = `
        <div style="font-size: 40px; margin-bottom: 20px;">⏳</div>
        <p style="color: #007aff; margin-bottom: 8px; font-weight: 600;">Caricamento in corso...</p>
        <div class="upload-progress" style="width: 0%; height: 4px; background: #007aff; margin: 20px auto; border-radius: 2px; max-width: 200px; display: block;"></div>
      `;

      // Create form data
      const formData = new FormData();
      formData.append('image', file);

      // If there's already an image uploaded, send its key for deletion
      const imageKeyInput = document.querySelector('input[name="image_key"]');
      if (imageKeyInput && imageKeyInput.value) {
        formData.append('previous_image_key', imageKeyInput.value);
        console.log('Will delete previous image:', imageKeyInput.value);
      }

      // Upload with progress tracking
      const xhr = await this.uploadWithProgress('/api/upload-bundle-image', formData, (progress) => {
        const progressBar = uploadArea.querySelector('.upload-progress');
        if (progressBar) {
          progressBar.style.width = `${progress}%`;
        }
      });

      console.log('Upload response status:', xhr.status);
      console.log('Upload response text:', xhr.responseText);
      
      const result = JSON.parse(xhr.responseText);
      console.log('Upload result:', result);

      if (result.success) {
        // Update the image key field
        if (imageKeyInput) {
          imageKeyInput.value = result.image_key;
        }

        // Show preview
        this.showImagePreview(result.image_url);
        
        toastManager.show('Immagine caricata con successo!', 'success');
      } else {
        throw new Error(result.error || 'Errore durante il caricamento');
      }
    } catch (error) {
      console.error('Upload error:', error);
      toastManager.show('Errore durante il caricamento dell\'immagine', 'error');
      
      // Reset upload area on error
      this.resetUploadArea();
    } finally {
      this.isUploading = false;
      // Clear file input to allow re-uploading the same file
      fileInput.value = '';
    }
  }

  async uploadWithProgress(url, formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const progress = (e.loaded / e.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr);
        } else {
          reject(new Error(`HTTP ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Network error')));
      
      xhr.open('POST', url);
      xhr.send(formData);
    });
  }

  showImagePreview(imageUrl) {
    const uploadArea = document.getElementById('image-upload-area');
    
    // Update the upload area with the new image
    uploadArea.innerHTML = `
      <img src="${imageUrl}" style="max-width: 100%; max-height: 200px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);" />
      <p style="color: #34c759; margin-top: 16px; font-weight: 600;">✅ Immagine caricata con successo!</p>
      <p style="color: #6c757d; font-size: 14px; margin-top: 8px;">Clicca per cambiare immagine</p>
      <div class="upload-progress" style="width: 0%; height: 4px; background: #007aff; margin-top: 20px; border-radius: 2px; display: none;"></div>
    `;
  }

  resetUploadArea() {
    const uploadArea = document.getElementById('image-upload-area');
    
    // Reset to initial state
    uploadArea.innerHTML = `
      <div style="font-size: 60px; margin-bottom: 20px;">📸</div>
      <p style="color: #1d1d1f; margin-bottom: 8px; font-weight: 600; font-size: 16px;">Clicca per caricare un'immagine</p>
      <p style="color: #6c757d; font-size: 14px; margin-bottom: 0;">o trascina qui il file (max 5MB)</p>
      <div class="upload-progress" style="width: 0%; height: 4px; background: #007aff; margin-top: 20px; border-radius: 2px; display: none;"></div>
    `;
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 Initializing Beat Management System...');
  
  window.beatManager = new BeatManager();
  window.imageUploadManager = new ImageUploadManager();
  
  console.log('✅ BeatManager instance created:', window.beatManager);
  
  // Add listener for "Save All" button (both desktop and mobile)
  const saveAllBtn = document.getElementById('save-all-btn');
  const mobileSaveAllBtn = document.getElementById('mobile-save-all-btn');
  
  function handleSaveAllClick() {
    console.log('🔄 Save All button clicked, calling beatManager.saveAllBeats()');
    if (window.beatManager && typeof window.beatManager.saveAllBeats === 'function') {
      window.beatManager.saveAllBeats();
    } else {
      console.error('❌ beatManager.saveAllBeats is not available');
      toastManager.show('Errore: Sistema di gestione beat non disponibile', 'error', {
        title: 'Errore Sistema'
      });
    }
  }
  
  if (saveAllBtn) {
    console.log('✅ Desktop Save All button found, adding event listener');
    saveAllBtn.addEventListener('click', handleSaveAllClick);
  } else {
    console.warn('⚠️ Desktop Save All button not found on this page');
  }
  
  if (mobileSaveAllBtn) {
    console.log('✅ Mobile Save All button found, adding event listener');
    mobileSaveAllBtn.addEventListener('click', handleSaveAllClick);
  } else {
    console.warn('⚠️ Mobile Save All button not found on this page');
  }
  
  // Add some helpful keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + S to save all
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      console.log('⌨️ Keyboard shortcut Ctrl+S pressed');
      if (window.beatManager && typeof window.beatManager.saveAllBeats === 'function') {
        window.beatManager.saveAllBeats();
      }
    }
    
    // Escape to clear all toasts
    if (e.key === 'Escape') {
      toastManager.clear();
    }
  });

  // Handle visibility change to pause/resume operations
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      // Page is hidden, could pause auto-refresh if implemented
    } else {
      // Page is visible again
    }
  });

  // Add touch feedback for mobile
  if ('ontouchstart' in window) {
    document.addEventListener('touchstart', (e) => {
      if (e.target.matches('button, .checkbox-label, input[type="submit"]')) {
        e.target.style.transform = 'scale(0.98)';
      }
    });

    document.addEventListener('touchend', (e) => {
      if (e.target.matches('button, .checkbox-label, input[type="submit"]')) {
        setTimeout(() => {
          e.target.style.transform = '';
        }, 100);
      }
    });
  }

  console.log('🎵 Enhanced Beat Management System initialized successfully!');
});

// Export for potential external use
window.BeatManagement = {
  toastManager,
  errorHandler,
  loadingManager,
  validator
};

// Aggiorna la percentuale di sconto in base ai prezzi
function updateDiscountPercent(id) {
  const originalInput = document.querySelector(`input.original-price[data-id='${id}']`);
  const discountedInput = document.querySelector(`input.discounted-price[data-id='${id}']`);
  const percentInput = document.querySelector(`input.discount-percent[data-id='${id}']`);
  const discountedCheckbox = document.querySelector(`input.is-discounted[data-id='${id}']`);

  let original = parseFloat(originalInput?.value) || 0;
  let discounted = parseFloat(discountedInput?.value) || 0;

  // Errore visivo: prezzo scontato negativo
  if (discountedCheckbox?.checked && discounted < 0) {
    errorHandler.showError(id, "Il prezzo scontato non può essere negativo.");
    discountedInput.value = '';
    percentInput.value = 0;
    return;
  }

  // Errore visivo: prezzo scontato >= originale
  if (discountedCheckbox?.checked && original > 0 && discounted >= original) {
    errorHandler.showError(id, "Il prezzo scontato deve essere minore del prezzo originale.");
    percentInput.value = 0;
    return;
  }

  if (discountedCheckbox?.checked && original > 0 && discounted > 0 && discounted < original) {
    let percent = Math.round((1 - discounted / original) * 100);
    percentInput.value = percent > 0 ? percent : 0;
  } else {
    percentInput.value = 0;
  }
}

// Quando cambia il prezzo originale o scontato aggiorna la percentuale e gestisci errori
document.addEventListener('input', (e) => {
  if (e.target.classList.contains('original-price') || e.target.classList.contains('discounted-price')) {
    const id = e.target.dataset.id;
    updateDiscountPercent(id);
  }
});

// Quando cambia la checkbox scontato, aggiorna la percentuale
document.addEventListener('change', (e) => {
  if (e.target.classList.contains('is-discounted')) {
    const id = e.target.dataset.id;
    updateDiscountPercent(id);
  }
});

// Abilita/disabilita il campo prezzo scontato in base alla checkbox "Scontato"
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.is-discounted').forEach(checkbox => {
    const id = checkbox.dataset.id;
    const discountedInput = document.querySelector(`input.discounted-price[data-id='${id}']`);
    if (discountedInput) {
      discountedInput.disabled = !checkbox.checked;
    }
    checkbox.addEventListener('change', () => {
      if (discountedInput) {
        discountedInput.disabled = !checkbox.checked;
        if (!checkbox.checked) {
          discountedInput.value = '';
        }
      }
    });
  });
});

// Database Operations
async function updateDatabase() {
  const button = document.getElementById('update-db-btn');
  if (!button) return;

  loadingManager.showButtonLoading(button);
  loadingManager.showOverlay();

  // Show progress bar
  const progressBar = document.querySelector('.progress-fill');
  const progressText = document.querySelector('.progress-text');
  const statusText = document.querySelector('.status-text');
  
  if (progressBar && progressText && statusText) {
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
    statusText.textContent = 'Scansione in corso su Google Drive...';
    
    // Simulate progress updates for better UX
    let progress = 0;
    const progressInterval = setInterval(() => {
      progress += Math.random() * 5;
      if (progress > 90) progress = 90; // Don't go over 90% until real completion
      
      progressBar.style.width = `${progress}%`;
      progressText.textContent = `${Math.round(progress)}%`;
      
      if (progress > 30) statusText.textContent = 'Processando file da Google Drive...';
      if (progress > 60) statusText.textContent = 'Caricamento su Cloudflare R2...';
      if (progress > 80) statusText.textContent = 'Aggiornamento database...';
    }, 500);

    try {
      console.log('🔄 Starting database update...');
      
      const response = await fetch('/admin/update-database', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const result = await response.json();
      
      // Clear progress simulation
      clearInterval(progressInterval);
      
      if (result.success) {
        // Complete progress
        progressBar.style.width = '100%';
        progressText.textContent = '100%';
        statusText.textContent = 'Aggiornamento completato!';
        
        setTimeout(() => {
          loadingManager.hideOverlay();
          loadingManager.hideButtonLoading(button);
          
          toastManager.show(result.message || 'Database aggiornato con successo!', 'success', {
            title: 'Aggiornamento Completato',
            duration: 5000
          });
          
          // Show details if available
          if (result.details) {
            console.log('📊 Update details:', result.details);
            toastManager.show(result.details, 'info', {
              title: 'Dettagli Aggiornamento',
              duration: 8000
            });
          }
          
          // Refresh page to show updated stats
          setTimeout(() => {
            window.location.reload();
          }, 2000);
        }, 1000);
      } else {
        throw new Error(result.error || 'Errore durante l\'aggiornamento del database');
      }
      
    } catch (error) {
      clearInterval(progressInterval);
      console.error('❌ Database update error:', error);
      
      // Show error in progress bar
      progressBar.style.width = '100%';
      progressBar.style.backgroundColor = '#ff3b30';
      progressText.textContent = 'Errore!';
      statusText.textContent = 'Errore durante l\'aggiornamento';
      
      setTimeout(() => {
        loadingManager.hideOverlay();
        loadingManager.hideButtonLoading(button);
        
        toastManager.show(error.message || 'Errore durante l\'aggiornamento del database', 'error', {
          title: 'Errore Aggiornamento Database',
          duration: 8000
        });
      }, 1000);
    }
  } else {
    // Fallback without progress bar
    try {
      const response = await fetch('/admin/update-database', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const result = await response.json();
      
      if (result.success) {
        loadingManager.hideOverlay();
        loadingManager.hideButtonLoading(button);
        
        toastManager.show(result.message || 'Database aggiornato con successo!', 'success', {
          title: 'Aggiornamento Completato'
        });
        
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else {
        throw new Error(result.error || 'Errore durante l\'aggiornamento del database');
      }
      
    } catch (error) {
      console.error('❌ Database update error:', error);
      toastManager.show(error.message || 'Errore durante l\'aggiornamento del database', 'error', {
        title: 'Errore Aggiornamento Database'
      });
      loadingManager.hideButtonLoading(button);
      loadingManager.hideOverlay();
    }
  }
}

async function resetDatabase() {
  const button = document.getElementById('reset-db-btn');
  if (!button) return;

  // Confirm action with custom modal
  const confirmed = await modalManager.confirm(
    'Conferma Reset Database',
    'Sei sicuro di voler resettare il database? Questa operazione cancellerà tutti i dati esistenti!',
    { 
      confirmText: 'Sì, Reset',
      cancelText: 'Annulla' 
    }
  );
  
  if (!confirmed) {
    return;
  }

  loadingManager.showButtonLoading(button);
  loadingManager.showOverlay();

  try {
    console.log('🔄 Starting database reset...');
    
    // Update progress manually since reset doesn't use SSE
    const progressBar = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    const statusText = document.querySelector('.status-text');
    
    if (progressBar && progressText && statusText) {
      progressBar.style.width = '0%';
      progressText.textContent = '0%';
      statusText.textContent = 'Reset database in corso...';
      
      // Simulate progress during reset
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress += 10;
        if (progress <= 90) {
          progressBar.style.width = `${progress}%`;
          progressText.textContent = `${progress}%`;
          statusText.textContent = progress < 50 ? 'Eliminazione tabelle...' : 'Ricreazione schema...';
        }
      }, 200);
      
      const response = await fetch('/admin/reset-database', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('📊 Reset result:', result);
      
      if (result.success) {
        // Complete progress
        progressBar.style.width = '100%';
        progressText.textContent = '100%';
        statusText.textContent = 'Reset completato!';
        
        // Update statistics in real time
        updateDatabaseStats();
        
        setTimeout(() => {
          loadingManager.hideOverlay();
          loadingManager.hideButtonLoading(button);
          
          toastManager.show(result.message || 'Database resettato con successo!', 'success', {
            title: 'Reset Completato'
          });
          
          // Refresh page to show updated stats
          setTimeout(() => {
            window.location.reload();
          }, 2000);
        }, 1000);
      } else {
        throw new Error(result.error || 'Errore durante il reset del database');
      }
    }

  } catch (error) {
    console.error('❌ Database reset error:', error);
    toastManager.show(error.message || 'Errore durante il reset del database', 'error', {
      title: 'Errore Reset Database'
    });
    loadingManager.hideButtonLoading(button);
    loadingManager.hideOverlay();
  }
}

// Function to update database statistics in real time
async function updateDatabaseStats() {
  try {
    const response = await fetch('/admin/database-stats', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (response.ok) {
      const stats = await response.json();
      
      // Update stat cards with animation
      const statCards = document.querySelectorAll('.stat-number');
      if (statCards.length >= 4) {
        // Animate the stats update
        statCards[0].style.transition = 'all 0.5s ease';
        statCards[1].style.transition = 'all 0.5s ease';
        statCards[2].style.transition = 'all 0.5s ease';
        statCards[3].style.transition = 'all 0.5s ease';
        
        // Update values
        statCards[0].textContent = stats.total_beats || 0;
        statCards[1].textContent = stats.exclusive_beats || 0;
        statCards[2].textContent = stats.active_bundles || 0;
        statCards[3].textContent = stats.sold_exclusive_count || 0;
        
        // Add visual feedback
        statCards.forEach(card => {
          card.style.transform = 'scale(1.1)';
          setTimeout(() => {
            card.style.transform = 'scale(1)';
          }, 200);
        });
      }
    }
  } catch (error) {
    console.error('Error updating database stats:', error);
  }
}

// Database operations are now synchronous - no progress tracking needed