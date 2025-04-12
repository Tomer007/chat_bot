import { ChatUI } from '../chatUI.js';

describe('ChatUI', () => {
  let chatUI;
  let mockElement;

  beforeEach(() => {
    // Reset localStorage mock
    localStorage.clear();
    localStorage.getItem.mockClear();
    localStorage.setItem.mockClear();

    // Create mock elements
    document.body.innerHTML = `
      <div id="chat-container">
        <button id="theme-toggle">Toggle Theme</button>
        <div id="chat-messages"></div>
        <textarea id="user-input"></textarea>
        <button id="send-button">Send</button>
      </div>
    `;

    // Initialize ChatUI
    chatUI = new ChatUI();
    chatUI.init();
  });

  describe('Theme Management', () => {
    test('should initialize with light theme by default', () => {
      expect(document.documentElement.classList.contains('dark-theme')).toBe(false);
    });

    test('should toggle theme when theme button is clicked', () => {
      const themeButton = document.getElementById('theme-toggle');
      themeButton.click();
      expect(document.documentElement.classList.contains('dark-theme')).toBe(true);
      expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark');
    });

    test('should load saved theme from localStorage', () => {
      localStorage.getItem.mockReturnValue('dark');
      chatUI = new ChatUI();
      chatUI.init();
      expect(document.documentElement.classList.contains('dark-theme')).toBe(true);
    });
  });

  describe('Message Handling', () => {
    test('should add user message to chat', () => {
      const userInput = document.getElementById('user-input');
      const sendButton = document.getElementById('send-button');
      
      userInput.value = 'Hello, chatbot!';
      sendButton.click();

      const messages = document.getElementById('chat-messages');
      expect(messages.children.length).toBe(1);
      expect(messages.children[0].classList.contains('user-message')).toBe(true);
    });

    test('should clear input after sending message', () => {
      const userInput = document.getElementById('user-input');
      const sendButton = document.getElementById('send-button');
      
      userInput.value = 'Test message';
      sendButton.click();

      expect(userInput.value).toBe('');
    });

    test('should handle empty messages', () => {
      const userInput = document.getElementById('user-input');
      const sendButton = document.getElementById('send-button');
      
      userInput.value = '';
      sendButton.click();

      const messages = document.getElementById('chat-messages');
      expect(messages.children.length).toBe(0);
    });
  });

  describe('Session Management', () => {
    test('should check session status on initialization', () => {
      expect(fetch).toHaveBeenCalledWith('/check_session', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });
    });

    test('should redirect to login if session is invalid', async () => {
      fetch.mockImplementationOnce(() =>
        Promise.resolve({
          ok: false,
          status: 401
        })
      );

      // Mock window.location
      delete window.location;
      window.location = { href: '' };

      await chatUI.checkSession();
      expect(window.location.href).toBe('/login');
    });
  });
}); 