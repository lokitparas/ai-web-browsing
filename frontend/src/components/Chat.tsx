import React, { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage, StatusUpdate } from '@/types';

interface ChatProps {
  messages: ChatMessage[];
  status: StatusUpdate | null;
}

const Chat: React.FC<ChatProps> = ({ messages, status }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 flex flex-col">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <p className="text-lg">Enter a URL and task to get started</p>
            <p className="text-sm mt-2">
              Example: Find the pricing information for enterprise plan
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mt-4 text-sm text-blue-800 max-w-md">
              <p className="font-semibold">Tips:</p>
              <ul className="list-disc list-inside mt-1">
                <li>Some websites with strong security (like banks) may block this tool</li>
                <li>Try with simpler websites first</li>
                <li>Be patient as the agent analyzes the page</li>
                <li>Specific tasks work better than general ones</li>
              </ul>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`chat-message ${
                  message.type === 'user' ? 'user-message' : 'agent-message'
                } ${message.content.toLowerCase().includes('error') ? 'error-message' : ''}`}
              >
                {message.type === 'agent' && message.content.toLowerCase().includes('error') ? (
                  <div>
                    <div className="font-bold text-red-600 mb-1">Error Encountered</div>
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                    <div className="mt-2 text-sm bg-red-50 p-2 rounded-md border border-red-200">
                      <p className="font-semibold">Possible solutions:</p>
                      <ul className="list-disc list-inside mt-1">
                        <li>Try a different website that has less security measures</li>
                        <li>Try a simpler task</li>
                        <li>Refresh the page and try again</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                )}
              </div>
            ))}
            {status && (
              <div className={`status-indicator ${status.status.toLowerCase().includes('error') ? 'text-red-500' : ''}`}>
                {status.status}
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
    </div>
  );
};

export default Chat; 