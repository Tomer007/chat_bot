import { DialogManager } from '../dialogManager.js';

describe('DialogManager', () => {
  let dialogManager;

  beforeEach(() => {
    // Create mock elements
    document.body.innerHTML = `
      <div id="help-dialog" class="dialog">
        <div class="dialog-content">
          <h2>Help</h2>
          <div class="dialog-body">
            <p>Help content</p>
          </div>
          <button class="close-button">Close</button>
        </div>
      </div>
      <div id="about-dialog" class="dialog">
        <div class="dialog-content">
          <h2>About</h2>
          <div class="dialog-body">
            <p>About content</p>
          </div>
          <button class="close-button">Close</button>
        </div>
      </div>
      <div id="overlay"></div>
    `;

    // Initialize DialogManager
    dialogManager = new DialogManager();
    dialogManager.init();
  });

  describe('Dialog Management', () => {
    test('should show help dialog', () => {
      dialogManager.showHelp();
      const helpDialog = document.getElementById('help-dialog');
      const overlay = document.getElementById('overlay');
      
      expect(helpDialog.style.display).toBe('block');
      expect(overlay.style.display).toBe('block');
    });

    test('should show about dialog', () => {
      dialogManager.showAbout();
      const aboutDialog = document.getElementById('about-dialog');
      const overlay = document.getElementById('overlay');
      
      expect(aboutDialog.style.display).toBe('block');
      expect(overlay.style.display).toBe('block');
    });

    test('should close dialog when close button is clicked', () => {
      dialogManager.showHelp();
      const closeButton = document.querySelector('#help-dialog .close-button');
      closeButton.click();

      const helpDialog = document.getElementById('help-dialog');
      const overlay = document.getElementById('overlay');
      
      expect(helpDialog.style.display).toBe('none');
      expect(overlay.style.display).toBe('none');
    });

    test('should close dialog when clicking outside', () => {
      dialogManager.showHelp();
      const overlay = document.getElementById('overlay');
      overlay.click();

      const helpDialog = document.getElementById('help-dialog');
      
      expect(helpDialog.style.display).toBe('none');
      expect(overlay.style.display).toBe('none');
    });

    test('should not close dialog when clicking inside', () => {
      dialogManager.showHelp();
      const dialogContent = document.querySelector('#help-dialog .dialog-content');
      dialogContent.click();

      const helpDialog = document.getElementById('help-dialog');
      const overlay = document.getElementById('overlay');
      
      expect(helpDialog.style.display).toBe('block');
      expect(overlay.style.display).toBe('block');
    });
  });

  describe('Keyboard Navigation', () => {
    test('should close dialog when Escape key is pressed', () => {
      dialogManager.showHelp();
      const event = new KeyboardEvent('keydown', { key: 'Escape' });
      document.dispatchEvent(event);

      const helpDialog = document.getElementById('help-dialog');
      const overlay = document.getElementById('overlay');
      
      expect(helpDialog.style.display).toBe('none');
      expect(overlay.style.display).toBe('none');
    });

    test('should not close dialog when other keys are pressed', () => {
      dialogManager.showHelp();
      const event = new KeyboardEvent('keydown', { key: 'Enter' });
      document.dispatchEvent(event);

      const helpDialog = document.getElementById('help-dialog');
      const overlay = document.getElementById('overlay');
      
      expect(helpDialog.style.display).toBe('block');
      expect(overlay.style.display).toBe('block');
    });
  });
}); 