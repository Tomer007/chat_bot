// Chat UI Module
export class ChatUI {
  constructor() {
    this.waitingForBot = false;
    this.dialogManager = new DialogManager();
    this.themeManager = new ThemeManager();
    this.transcriptManager = new TranscriptManager();
    this.recognition = null;
    this.isRecording = false;
    this.micButton = document.getElementById('micButton');
    this.userInput = document.getElementById('userInput');
    this.fileInput = document.getElementById('fileInput');
    this.uploadButton = document.getElementById('uploadButton');
    this.uploadedFileContent = null;
    this.attachedFileName = null; // Initialize the property

    // Elements
    this.micButton = document.getElementById('micButton');
    this.userInput = document.getElementById('userInput');
    this.fileInput = document.getElementById('fileInput');
    this.uploadButton = document.getElementById('uploadButton');

    // Add session check interval
    this.setupSessionCheck();
  }


  init() {
    this.setupEventListeners();
    this.setupAutoResize();
    this.setupMenuItems();
    this.setupVoiceRecognition();
    this.setupFileUpload();
  }

  setupEventListeners() {
    console.log('Setting up event listeners...'); // Debug log

    // Hamburger menu setup
    const hamburgerIcon = document.getElementById('hamburgerIcon');
    const menuContent = document.getElementById('menuContent');
    const overlay = document.getElementById('menuOverlay');
    
    console.log('Hamburger menu elements:', {
      hamburgerIcon: hamburgerIcon ? 'found' : 'not found',
      menuContent: menuContent ? 'found' : 'not found',
      overlay: overlay ? 'found' : 'not found'
    });
    
    // Only set up hamburger menu if all required elements exist
    if (hamburgerIcon && menuContent) {
      console.log('Setting up hamburger menu event listeners');
      hamburgerIcon.addEventListener('click', () => {
        // Toggle menu visibility
        if (menuContent.classList.contains('active')) {
          // Close menu if it's already open
          menuContent.classList.remove('active');
          if (overlay) {
            overlay.classList.remove('active');
          }
        } else {
          // Open menu if it's closed
          menuContent.classList.add('active');
          if (overlay) {
            overlay.classList.add('active');
          }
        }
      });
      
      // If overlay exists, set up click event
      if (overlay) {
        overlay.addEventListener('click', () => {
          menuContent.classList.remove('active');
          overlay.classList.remove('active');
        });
      }
      
      // Close menu when clicking outside
      document.addEventListener('click', (e) => {
        if (menuContent.classList.contains('active') && 
            !menuContent.contains(e.target) && 
            e.target !== hamburgerIcon && 
            !hamburgerIcon.contains(e.target)) {
          menuContent.classList.remove('active');
          if (overlay) {
            overlay.classList.remove('active');
          }
        }
      });
      
      // Set up menu item click handlers
      const menuItems = document.querySelectorAll('.menu-item');
      menuItems.forEach(item => {
        item.addEventListener('click', () => {
          // Close the menu when any menu item is clicked
          menuContent.classList.remove('active');
          if (overlay) {
            overlay.classList.remove('active');
          }
        });
      });
    }

    // Chat input
    const textarea = this.userInput;
    const sendButton = document.getElementById('sendButton');

    if (!textarea || !sendButton) {
      console.error('Required elements not found:', { textarea, sendButton }); // Debug log
      return;
    }

    console.log('Found required elements'); // Debug log

    // Handle Enter key press
    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        console.log('Enter key pressed'); // Debug log
        this.sendMessage();
      }
    });

    // Handle send button click
    sendButton.addEventListener('click', (e) => {
      e.preventDefault();
      console.log('Send button clicked'); // Debug log
      this.sendMessage();
    });

    // NOTE: The mic button event listener is now only set in setupVoiceRecognition method
  }

  setupMenuItems() {
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const action = item.dataset.action;
        this.handleMenuAction(action);
      });
    });
  }

  handleMenuAction(action) {
    switch (action) {
      case 'download':
        this.transcriptManager.downloadTranscript();
        break;
      case 'help':
        this.dialogManager.showHelp();
        break;
      case 'about':
        this.dialogManager.showAbout();
        break;
      case 'theme':
        this.themeManager.toggleDarkMode();
        break;
      case 'logout':
        window.location.href = '/auth/logout';
        break;
    }
  }

  setupSessionCheck() {
    const checkSession = () => {
      fetch('/auth/check_session')
        .then(response => {
          if (response.status === 403) {
            window.location.href = '/auth/login';
          }
        })
        .catch(() => {
          window.location.href = '/auth/login';
        });
    };

    // Check session every 5 minutes
    setInterval(checkSession, 300000);
  }

  setupAutoResize() {
    const textarea = this.userInput;
    const charCounter = document.querySelector('.char-counter');
    const maxLength = parseInt(textarea.getAttribute('maxlength')) || 1000;

    const updateCounter = () => {
      const currentLength = textarea.value.length;
      charCounter.textContent = `${currentLength}/${maxLength}`;

      if (currentLength > maxLength * 0.9) {
        charCounter.classList.add('warning');
      } else {
        charCounter.classList.remove('warning');
      }
    };

    textarea.addEventListener('input', () => {
      // Auto-resize
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';

      // Update character counter
      updateCounter();
    });

    // Initial counter update
    updateCounter();
  }

  autoResize() {
    const textarea = this.userInput;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }

  setupVoiceRecognition() {
    this.recognition = null;
    this.isRecording = false;
    this.micButton = document.getElementById('micButton');
    this.userInput = document.getElementById('userInput');

    // Check if browser supports speech recognition
    if ('webkitSpeechRecognition' in window) {
      this.recognition = new webkitSpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'he-IL'; // Hebrew language code

      this.recognition.onstart = () => {
        this.isRecording = true;
        this.micButton.classList.add('recording');
        this.micButton.title = 'מקליט... לחץ להפסקת ההקלטה';
        console.log('Voice recognition started');
      };

      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        console.log('Language:', this.recognition.lang);
        console.log('Transcript:', transcript);

        // Update input with transcript
        this.userInput.value = transcript;
        this.autoResize();

        // Show success message
        this.showSuccess('ההודעה הוקלטה בהצלחה');
      };

      this.recognition.onerror = (event) => {
        console.error('Voice recognition error:', event.error);
        this.stopRecording();

        // Show appropriate error message based on error type
        let errorMessage = 'שגיאה בהקלטה. אנא נסה שוב.';
        switch(event.error) {
          case 'no-speech':
            errorMessage = 'לא זוהה קול. אנא נסה שוב.';
            break;
          case 'audio-capture':
            errorMessage = 'לא ניתן לגשת למיקרופון. אנא בדוק את ההרשאות.';
            break;
          case 'not-allowed':
            errorMessage = 'הגישה למיקרופון נדחתה. אנא אשר את ההרשאה.';
            break;
        }
        this.showError(errorMessage);
      };

      this.recognition.onend = () => {
        this.stopRecording();
      };

      this.micButton.addEventListener('click', () => {
        if (this.isRecording) {
          this.stopRecording();
        } else {
          this.startRecording();
        }
      });
    } else {
      // Hide microphone button if speech recognition is not supported
      this.micButton.style.display = 'none';
      console.warn('Speech recognition not supported in this browser');
    }
  }

  startRecording() {
    if (this.recognition) {
      try {
        this.recognition.start();
      } catch (error) {
        console.error('Error starting recognition:', error);
        this.showError('לא ניתן להתחיל הקלטה. אנא נסה שוב.');
      }
    }
  }

  stopRecording() {
    if (this.recognition) {
      this.recognition.stop();
      this.isRecording = false;
      this.micButton.classList.remove('recording');
      this.micButton.title = 'הקלטה קולית';
    }
  }

  showError(message) {
    // Create toast-style error notification
    const errorDiv = document.createElement('div');
    errorDiv.className = 'toast-notification error-toast';
    
    // Add icon and message in a flex container
    errorDiv.innerHTML = `
      <div class="toast-icon">⚠️</div>
      <div class="toast-text">${message}</div>
    `;

    // Create or get toast container
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.style.position = 'fixed';
      toastContainer.style.bottom = '20px';
      toastContainer.style.left = '50%';
      toastContainer.style.transform = 'translateX(-50%)';
      toastContainer.style.zIndex = '9999';
      toastContainer.style.display = 'flex';
      toastContainer.style.flexDirection = 'column';
      toastContainer.style.alignItems = 'center';
      toastContainer.style.gap = '10px';
      document.body.appendChild(toastContainer);
    }

    // Add to toast container
    toastContainer.appendChild(errorDiv);

    // Style the toast
    errorDiv.style.backgroundColor = 'var(--error-bg, #ff5252)';
    errorDiv.style.color = 'var(--error-text, white)';
    errorDiv.style.padding = '12px 20px';
    errorDiv.style.borderRadius = '8px';
    errorDiv.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    errorDiv.style.display = 'flex';
    errorDiv.style.alignItems = 'center';
    errorDiv.style.gap = '10px';
    errorDiv.style.minWidth = '280px';
    errorDiv.style.maxWidth = '380px';
    errorDiv.style.transform = 'translateY(100px)';
    errorDiv.style.opacity = '0';
    errorDiv.style.transition = 'transform 0.3s ease, opacity 0.3s ease';

    // Animate in
    setTimeout(() => {
      errorDiv.style.transform = 'translateY(0)';
      errorDiv.style.opacity = '1';
    }, 10);

    // Remove after delay with animation
    setTimeout(() => {
      errorDiv.style.transform = 'translateY(100px)';
      errorDiv.style.opacity = '0';
      setTimeout(() => {
        errorDiv.remove();
        // Remove container if empty
        if (toastContainer.children.length === 0) {
          toastContainer.remove();
        }
      }, 300);
    }, 3000);
  }

  showSuccess(message) {
    // Create toast-style success notification
    const successDiv = document.createElement('div');
    successDiv.className = 'toast-notification success-toast';
    
    // Add icon and message in a flex container
    successDiv.innerHTML = `
      <div class="toast-icon">✅</div>
      <div class="toast-text">${message}</div>
    `;

    // Create or get toast container
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.style.position = 'fixed';
      toastContainer.style.bottom = '20px';
      toastContainer.style.left = '50%';
      toastContainer.style.transform = 'translateX(-50%)';
      toastContainer.style.zIndex = '9999';
      toastContainer.style.display = 'flex';
      toastContainer.style.flexDirection = 'column';
      toastContainer.style.alignItems = 'center';
      toastContainer.style.gap = '10px';
      document.body.appendChild(toastContainer);
    }

    // Add to toast container
    toastContainer.appendChild(successDiv);

    // Style the toast
    successDiv.style.backgroundColor = 'var(--success-bg, #4caf50)';
    successDiv.style.color = 'var(--success-text, white)';
    successDiv.style.padding = '12px 20px';
    successDiv.style.borderRadius = '8px';
    successDiv.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    successDiv.style.display = 'flex';
    successDiv.style.alignItems = 'center';
    successDiv.style.gap = '10px';
    successDiv.style.minWidth = '280px';
    successDiv.style.maxWidth = '380px';
    successDiv.style.transform = 'translateY(100px)';
    successDiv.style.opacity = '0';
    successDiv.style.transition = 'transform 0.3s ease, opacity 0.3s ease';

    // Animate in
    setTimeout(() => {
      successDiv.style.transform = 'translateY(0)';
      successDiv.style.opacity = '1';
    }, 10);

    // Remove after delay with animation
    setTimeout(() => {
      successDiv.style.transform = 'translateY(100px)';
      successDiv.style.opacity = '0';
      setTimeout(() => {
        successDiv.remove();
        // Remove container if empty
        if (toastContainer.children.length === 0) {
          toastContainer.remove();
        }
      }, 300);
    }, 3000);
  }


  sendMessage() {
    const textarea = this.userInput;
    const message = textarea.value.trim();
    const file = this.fileInput ? this.fileInput.files[0] : null;

    if (!message && !file) return;

    // Disable input while sending
    textarea.disabled = true;
    const sendButton = document.getElementById('sendButton');
    if (sendButton) sendButton.disabled = true;

    // Add user's message to chat
    if (message) this.addMessage(message, 'user');

    // Clear input
    textarea.value = '';
    this.autoResize();

    // Prepare form data
    const formData = new FormData();
    formData.append('message', message);
    if (file) formData.append('file', file);

    // Send request
    fetch('/chat/input', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (response.status === 403) {
        window.location.href = '/auth/login';
        return;
      }
      return response.json();
    })
    .then(response => {
      if (response && response.message) {
        this.addMessage(response.message, 'bot');
      }
    })
    .catch(() => {
      this.showError('שגיאה בשליחת ההודעה. אנא נסה שוב.');
    })
    .finally(() => {
      // Re-enable input
      textarea.disabled = false;
      if (sendButton) sendButton.disabled = false;
      if (this.fileInput) this.fileInput.value = '';
      textarea.focus();
    });
  }

  getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  addMessage(text, sender) {
    const chatBox = document.querySelector('.chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    // Format the message text
    const formattedText = this.formatMessage(text);
    messageDiv.innerHTML = formattedText;

    // Add timestamp
    const timestamp = document.createElement('div');
    timestamp.className = 'timestamp';
    timestamp.textContent = this.getCurrentTimestamp();
    messageDiv.appendChild(timestamp);

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  formatMessage(text) {
    // Convert markdown to HTML
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
      .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
      .replace(/\n/g, '<br>'); // Line breaks
  }

  getCurrentTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString('he-IL', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  isHebrew(text) {
    return /[\u0590-\u05FF]/.test(text);
  }

  formatBotTextMarkdown(text) {
    const html = marked.parse(text);
    return `<div class="markdown-content">${html}</div>`;
  }


  setupFileUpload() {
    if (this.uploadButton && this.fileInput) {
      this.uploadButton.addEventListener('click', () => {
        this.fileInput.click();
      });

      this.fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
        this.selectedFile = file;
        this.attachedFileName = file.name;
        // Update the UI indicator
        this.updateFileAttachmentIndicator();
        }
      });
    }
  }

  uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    $.ajax({
      url: '/chat/upload',   // Updated endpoint URL
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      xhrFields: { withCredentials: true },

      success: (response) => {
        console.log('File upload successful:', response);
        if (response.success) {
          this.uploadedFileContent = response.text;
          this.attachedFileName = file.name; // Set the file name
          this.updateFileAttachmentIndicator(); // Update the indicator
        } else {
          this.showError('שגיאה בהעלאת הקובץ: ' + (response.error || ''));
        }
      },

      error: (xhr, status, error) => {
        console.error('Error uploading file:', error);
        this.showError('שגיאה בהעלאת הקובץ. אנא נסה שוב.');
      }
    });
  }
  updateFileAttachmentIndicator() {
    const textarea = this.userInput;
    if (!textarea) return;

    // Find or create the file attachment indicator
    let indicator = document.querySelector('.file-attachment-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'file-attachment-indicator';

      // Insert into the .input-footer so it's near the char counter
      // and not overlapping the send/mic buttons
      const footer = document.querySelector('.input-footer');
      if (footer) {
        footer.appendChild(indicator); // place after the char-counter
      } else {
        // fallback: place above the textarea
        textarea.parentNode.insertBefore(indicator, textarea);
      }
    }

    if (this.attachedFileName) {
      // Get file extension to determine icon
      const extension = this.attachedFileName.split('.').pop().toLowerCase();
      let fileIcon = '📄'; // Default document icon
      
      // Choose appropriate icon based on file type
      if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(extension)) {
        fileIcon = '🖼️'; // Image
      } else if (['mp4', 'avi', 'mov', 'wmv'].includes(extension)) {
        fileIcon = '🎬'; // Video
      } else if (['pdf'].includes(extension)) {
        fileIcon = '📑'; // PDF
      } else if (['doc', 'docx'].includes(extension)) {
        fileIcon = '📝'; // Word
      } else if (['xls', 'xlsx'].includes(extension)) {
        fileIcon = '📊'; // Excel
      } else if (['zip', 'rar', '7z', 'tar', 'gz'].includes(extension)) {
        fileIcon = '🗜️'; // Archive
      }

      // Construct the content for the indicator
      indicator.innerHTML = `
        <div class="file-attachment-content">
          <div class="attachment-icon">${fileIcon}</div>
          <span class="file-name">${this.attachedFileName}</span>
          <button class="remove-file" title="הסר קובץ">
            <span class="remove-icon">×</span>
          </button>
        </div>
      `;

      // Apply modern styling with CSS variables for theme consistency
      indicator.style.display = 'flex';
      indicator.style.alignItems = 'center';
      indicator.style.margin = '8px 0';
      indicator.style.animation = 'fadeIn 0.3s ease-in-out';

      // Modern file attachment styling
      const content = indicator.querySelector('.file-attachment-content');
      if (content) {
        content.style.display = 'flex';
        content.style.alignItems = 'center';
        content.style.gap = '8px';
        content.style.padding = '8px 12px';
        content.style.borderRadius = '8px';
        content.style.backgroundColor = 'var(--input-bg, #f0f2f5)';
        content.style.border = '1px solid var(--border-color, #e0e0e0)';
        content.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.05)';
      }
      
      // Style the filename
      const fileName = indicator.querySelector('.file-name');
      if (fileName) {
        fileName.style.fontSize = '14px';
        fileName.style.fontWeight = '500';
        fileName.style.color = 'var(--text-color, #333)';
        fileName.style.maxWidth = '180px';
        fileName.style.overflow = 'hidden';
        fileName.style.textOverflow = 'ellipsis';
        fileName.style.whiteSpace = 'nowrap';
      }

      // Style the remove button
      const removeButton = indicator.querySelector('.remove-file');
      if (removeButton) {
        removeButton.style.display = 'flex';
        removeButton.style.alignItems = 'center';
        removeButton.style.justifyContent = 'center';
        removeButton.style.width = '20px';
        removeButton.style.height = '20px';
        removeButton.style.borderRadius = '50%';
        removeButton.style.backgroundColor = 'var(--btn-bg, #e0e0e0)';
        removeButton.style.border = 'none';
        removeButton.style.cursor = 'pointer';
        removeButton.style.transition = 'all 0.2s ease';
        
        // Hover effect
        removeButton.addEventListener('mouseenter', () => {
          removeButton.style.backgroundColor = 'var(--btn-hover-bg, #d0d0d0)';
        });
        
        removeButton.addEventListener('mouseleave', () => {
          removeButton.style.backgroundColor = 'var(--btn-bg, #e0e0e0)';
        });
        
        // Add click handler
        removeButton.addEventListener('click', () => {
          this.removeAttachedFile();
        });
      }
    } else {
      // No file => hide
      indicator.style.display = 'none';
    }
  }

  removeAttachedFile() {
    if (this.fileInput) {
      this.fileInput.value = '';
    }
    this.uploadedFileContent = null;
    this.attachedFileName = null;
    this.updateFileAttachmentIndicator();
  }
}

// Dialog Module
export class DialogManager {
  constructor() {
    this.init();
  }

  init() {
    this.setupDialogEventListeners();
  }

  setupDialogEventListeners() {
    const overlay = document.getElementById('dialogOverlay');
    const helpDialog = document.getElementById('helpDialog');
    const aboutDialog = document.getElementById('aboutDialog');

    if (overlay) {
      overlay.addEventListener('click', () => this.closeAllDialogs());
    }

    // Add close button event listeners
    const closeButtons = document.querySelectorAll('.close-button');
    closeButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const dialog = button.closest('.dialog');
        if (dialog) {
          dialog.style.display = 'none';
          overlay.style.display = 'none';
        }
      });
    });

    // Prevent dialog content clicks from closing
    if (helpDialog) {
      helpDialog.addEventListener('click', (e) => e.stopPropagation());
    }
    if (aboutDialog) {
      aboutDialog.addEventListener('click', (e) => e.stopPropagation());
    }

    // Add keyboard event listener for Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeAllDialogs();
      }
    });
  }

  showHelp() {
    const helpDialog = document.getElementById('helpDialog');
    const overlay = document.getElementById('dialogOverlay');
    if (helpDialog && overlay) {
      helpDialog.style.display = 'block';
      overlay.style.display = 'block';
    }
  }

  closeHelp() {
    const helpDialog = document.getElementById('helpDialog');
    const overlay = document.getElementById('dialogOverlay');
    if (helpDialog && overlay) {
      helpDialog.style.display = 'none';
      overlay.style.display = 'none';
    }
  }

  showAbout() {
    const aboutDialog = document.getElementById('aboutDialog');
    const overlay = document.getElementById('dialogOverlay');
    if (aboutDialog && overlay) {
      aboutDialog.style.display = 'block';
      overlay.style.display = 'block';
    }
  }

  closeAbout() {
    const aboutDialog = document.getElementById('aboutDialog');
    const overlay = document.getElementById('dialogOverlay');
    if (aboutDialog && overlay) {
      aboutDialog.style.display = 'none';
      overlay.style.display = 'none';
    }
  }

  closeAllDialogs() {
    this.closeHelp();
    this.closeAbout();
  }
}

// Theme Module
export class ThemeManager {
  constructor() {
    this.init();
  }

  init() {
    this.setupInitialTheme();
    this.setupThemeToggle();
  }

  setupInitialTheme() {
    const savedTheme = localStorage.getItem('theme');
    const themeIcon = document.querySelector('.theme-icon');
    const themeText = document.querySelector('.theme-text');

    // Always start with light mode if no theme is saved
    if (!savedTheme) {
      localStorage.setItem('theme', 'light');
    }

    // Apply the theme
    if (savedTheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      if (themeIcon) themeIcon.textContent = '☀️';
      if (themeText) themeText.textContent = 'מצב יום';
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      if (themeIcon) themeIcon.textContent = '🌙';
      if (themeText) themeText.textContent = 'מצב לילה';
    }
  }

  setupThemeToggle() {
    const btn = document.getElementById("toggleModeBtn");
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.toggleDarkMode();
      });
    }
  }

  toggleDarkMode() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const isDarkMode = currentTheme === 'light';
    const newTheme = isDarkMode ? 'dark' : 'light';

    document.documentElement.setAttribute('data-theme', newTheme);

    const themeIcon = document.querySelector('.theme-icon');
    const themeText = document.querySelector('.theme-text');

    if (themeIcon) themeIcon.textContent = isDarkMode ? '☀️' : '🌙';
    if (themeText) themeText.textContent = isDarkMode ? 'מצב יום' : 'מצב לילה';

    localStorage.setItem('theme', newTheme);
  }
}

// Transcript Module
export class TranscriptManager {
  downloadTranscript() {
    const messages = document.querySelectorAll('.message');
    let transcript = '';
    messages.forEach(msg => {
      const text = msg.innerText.trim();
      transcript += text + '\n\n';
    });
    const blob = new Blob([transcript], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chat_transcript.txt';
    a.click();
    URL.revokeObjectURL(url);
  }
}

// Initialize ChatUI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM loaded, initializing ChatUI...'); // Debug log
  const chatUI = new ChatUI();
  chatUI.init();
});

// Initialize theme manager separately to ensure it works
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM loaded, initializing ThemeManager...'); // Debug log
  const themeManager = new ThemeManager();
});

