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
    if (!beatData.originalPrice || beatData.originalPrice <= 0) {
      errors.push('Il prezzo originale deve essere maggiore di 0');
    }

    // Validate discount logic
    if (beatData.isDiscounted) {
      if (!beatData.discountedPrice || beatData.discountedPrice <= 0) {
        errors.push('Il prezzo scontato deve essere maggiore di 0');
      }
      
      if (beatData.discountedPrice >= beatData.originalPrice) {
        errors.push('Il prezzo scontato deve essere minore del prezzo originale');
      }
      
      if (!beatData.discountPercent || beatData.discountPercent <= 0 || beatData.discountPercent > 99) {
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

// Enhanced beat management with better UX
class BeatManager {
  constructor() {
    this.beats = new Map();
    this.initializeEventListeners();
    this.loadBeatsFromDOM();
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
      // Simulate API call
      await this.simulateApiCall(1000);
      
      errorHandler.showSuccess(`Beat salvato con successo!`);
      return true;
    } catch (error) {
      errorHandler.showError(beatId, 'Errore durante il salvataggio. Riprova.');
      return false;
    } finally {
      loadingManager.hideButtonLoading(button);
    }
  }

  async saveAllBeats() {
    const allBeats = Array.from(this.beats.keys()).map(id => this.getBeatDataFromDOM(id));
    const hasErrors = allBeats.some(beat => validator.validateBeat(beat).length > 0);

    if (hasErrors) {
      toastManager.show('Correggi tutti gli errori prima di salvare', 'error', {
        title: 'Validazione Fallita'
      });
      return false;
    }

    const button = document.getElementById('save-all-btn');
    loadingManager.showButtonLoading(button);
    loadingManager.showOverlay();

    try {
      // Simulate API call
      await this.simulateApiCall(2000);
      
      errorHandler.showSuccess('Tutti i beat sono stati salvati con successo!');
      return true;
    } catch (error) {
      toastManager.show('Errore durante il salvataggio. Riprova.', 'error', {
        title: 'Errore di Rete'
      });
      return false;
    } finally {
      loadingManager.hideButtonLoading(button);
      loadingManager.hideOverlay();
    }
  }

  simulateApiCall(delay) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        // Simulate occasional failures for demo
        if (Math.random() > 0.9) {
          reject(new Error('Network error'));
        } else {
          resolve();
        }
      }, delay);
    });
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

// Initialize beat manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const beatManager = new BeatManager();
  
  // Add some helpful keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + S to save all
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      beatManager.saveAllBeats();
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

  console.log('🎵 Beat Management System initialized successfully!');
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