import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function useKeyboardShortcuts() {
  const navigate = useNavigate();

  useEffect(() => {
    let gKeyPressed = false;

    const handleKeyDown = (event) => {
      // Ignore shortcuts when typing in inputs, textareas, or with modifiers
      if (
        event.target.tagName === 'INPUT' ||
        event.target.tagName === 'TEXTAREA' ||
        event.target.isContentEditable
      ) {
        // Allow '/' in search inputs
        if (event.key === '/' && event.target.id !== 'global-search') {
          return;
        }
        // Allow other shortcuts when not in search
        if (event.key !== '/' && event.key !== '?') {
          return;
        }
      }

      // Handle 'g' key for navigation sequences
      if (event.key === 'g' && !event.ctrlKey && !event.metaKey && !event.altKey) {
        gKeyPressed = true;
        setTimeout(() => {
          gKeyPressed = false;
        }, 1000);
        return;
      }

      // g + h: Go to home/dashboard
      if (gKeyPressed && event.key === 'h') {
        event.preventDefault();
        navigate('/');
        gKeyPressed = false;
        return;
      }

      // g + d: Go to deployments (same as home in this app)
      if (gKeyPressed && event.key === 'd') {
        event.preventDefault();
        navigate('/');
        gKeyPressed = false;
        return;
      }

      // g + n: Go to new deployment
      if (gKeyPressed && event.key === 'n') {
        event.preventDefault();
        navigate('/deploy');
        gKeyPressed = false;
        return;
      }

      // Single key shortcuts
      switch (event.key) {
        case '?':
          // Show keyboard shortcuts help
          event.preventDefault();
          window.dispatchEvent(new CustomEvent('show-shortcuts-modal'));
          break;

        case '/':
          // Focus global search
          event.preventDefault();
          const searchInput = document.getElementById('global-search');
          if (searchInput) {
            searchInput.focus();
          }
          break;

        case 'n':
          // New deployment (only if not in a text input)
          if (
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey &&
            event.target.tagName !== 'INPUT' &&
            event.target.tagName !== 'TEXTAREA'
          ) {
            event.preventDefault();
            navigate('/deploy');
          }
          break;

        case 'r':
          // Refresh page
          if (
            !event.ctrlKey &&
            !event.metaKey &&
            event.target.tagName !== 'INPUT' &&
            event.target.tagName !== 'TEXTAREA'
          ) {
            event.preventDefault();
            window.location.reload();
          }
          break;

        case 'Escape':
          // Close modals or unfocus inputs
          if (document.activeElement) {
            document.activeElement.blur();
          }
          window.dispatchEvent(new CustomEvent('close-modal'));
          break;

        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [navigate]);
}

export default useKeyboardShortcuts;
