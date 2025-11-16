import { useState, useEffect } from 'react';

const shortcuts = [
  {
    category: 'Navigation',
    items: [
      { keys: ['g', 'h'], description: 'Go to Dashboard' },
      { keys: ['g', 'd'], description: 'Go to Deployments' },
      { keys: ['g', 'n'], description: 'Go to New Deployment' },
      { keys: ['n'], description: 'New Deployment' },
    ],
  },
  {
    category: 'Actions',
    items: [
      { keys: ['r'], description: 'Refresh page' },
      { keys: ['/'], description: 'Focus search' },
      { keys: ['Esc'], description: 'Close modal / Unfocus' },
    ],
  },
  {
    category: 'Help',
    items: [
      { keys: ['?'], description: 'Show keyboard shortcuts' },
    ],
  },
];

function KeyboardShortcutsModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleShowModal = () => setIsOpen(true);
    const handleCloseModal = () => setIsOpen(false);

    window.addEventListener('show-shortcuts-modal', handleShowModal);
    window.addEventListener('close-modal', handleCloseModal);

    return () => {
      window.removeEventListener('show-shortcuts-modal', handleShowModal);
      window.removeEventListener('close-modal', handleCloseModal);
    };
  }, []);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
        onClick={() => setIsOpen(false)}
      ></div>

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl sm:p-6">
          {/* Header */}
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900" id="modal-title">
              Keyboard Shortcuts
            </h3>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <span className="sr-only">Close</span>
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Shortcuts List */}
          <div className="space-y-6">
            {shortcuts.map((section) => (
              <div key={section.category}>
                <h4 className="mb-3 text-sm font-semibold text-gray-700">
                  {section.category}
                </h4>
                <div className="space-y-2">
                  {section.items.map((shortcut, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2"
                    >
                      <span className="text-sm text-gray-700">{shortcut.description}</span>
                      <div className="flex items-center space-x-1">
                        {shortcut.keys.map((key, keyIndex) => (
                          <div key={keyIndex} className="flex items-center">
                            <kbd className="inline-flex items-center rounded border border-gray-300 bg-white px-2 py-1 font-mono text-xs font-medium text-gray-700 shadow-sm">
                              {key}
                            </kbd>
                            {keyIndex < shortcut.keys.length - 1 && (
                              <span className="mx-1 text-gray-400">then</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default KeyboardShortcutsModal;
