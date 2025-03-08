import React, { useState, useEffect } from 'react';
import { BrowsingTask } from '@/types';

interface TaskInputProps {
  onSubmit: (task: BrowsingTask) => void;
  isLoading: boolean;
  disabled?: boolean;
}

// List of domains with strong anti-automation measures
const restrictedDomains = [
  'chase.com',
  'bankofamerica.com',
  'wellsfargo.com',
  'citi.com',
  'americanexpress.com',
  'discover.com',
  'capitalone.com',
  'usbank.com',
  'paypal.com',
  'stripe.com',
  'coinbase.com',
  'robinhood.com'
];

const TaskInput: React.FC<TaskInputProps> = ({ onSubmit, isLoading, disabled = false }) => {
  const [url, setUrl] = useState('');
  const [instruction, setInstruction] = useState('');
  const [showWarning, setShowWarning] = useState(false);
  const [warningMessage, setWarningMessage] = useState('');
  
  // Check if domain has strong anti-automation measures
  useEffect(() => {
    if (!url) {
      setShowWarning(false);
      return;
    }
    
    try {
      const domain = new URL(url).hostname.replace('www.', '');
      const isRestricted = restrictedDomains.some(restrictedDomain => 
        domain === restrictedDomain || domain.endsWith(`.${restrictedDomain}`)
      );
      
      if (isRestricted) {
        setShowWarning(true);
        setWarningMessage(`Warning: ${domain} has strong anti-automation protections and may not work well with this tool. Consider using a different site for testing.`);
      } else {
        setShowWarning(false);
      }
    } catch (e) {
      // Not a valid URL yet, no warning needed
      setShowWarning(false);
    }
  }, [url]);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url && instruction) {
      onSubmit({ url, instruction });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="input-container">
      <div className="mb-4">
        <label htmlFor="url" className="block text-gray-700 text-sm font-medium mb-2">
          Website URL
        </label>
        <input
          id="url"
          type="url"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="https://example.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          disabled={isLoading || disabled}
        />
        {showWarning && (
          <div className="mt-2 text-sm text-amber-600 bg-amber-50 p-2 rounded-md border border-amber-200">
            {warningMessage}
          </div>
        )}
        {disabled && !isLoading && (
          <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded-md border border-red-200">
            Not connected to server. Please wait while we attempt to reconnect.
          </div>
        )}
      </div>
      
      <div className="mb-4">
        <label htmlFor="instruction" className="block text-gray-700 text-sm font-medium mb-2">
          What would you like to do?
        </label>
        <textarea
          id="instruction"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Find the pricing information for the enterprise plan"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={2}
          required
          disabled={isLoading || disabled}
        />
        <p className="mt-1 text-xs text-gray-500">
          Example tasks: "Find the pricing information", "Check the features of the product", "Find contact information"
        </p>
      </div>
      
      <button
        type="submit"
        className="w-full py-2 px-4 bg-primary-600 text-white font-medium rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
        disabled={isLoading || !url || !instruction || disabled}
      >
        {isLoading ? 'Working...' : disabled ? 'Reconnecting...' : 'Start Browsing'}
      </button>
    </form>
  );
};

export default TaskInput; 