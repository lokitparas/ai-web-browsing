import React, { useState, useEffect, useCallback, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import Chat from '@/components/Chat';
import Screenshot from '@/components/Screenshot';
import TaskInput from '@/components/TaskInput';
import {
  BrowsingTask,
  ChatMessage,
  ScreenshotData,
  StatusUpdate,
  WebSocketUpdate,
} from '@/types';

// Create a static websocket that persists across renders and hot module reloads
// This is necessary because in development mode, React renders components twice
let globalWebSocket: WebSocket | null = null;
let connectionAttemptCount = 0;
let connectionInProgress = false;

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [screenshot, setScreenshot] = useState<ScreenshotData | null>(null);
  const [status, setStatus] = useState<StatusUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<number>(0);
  const [connectionAttempts, setConnectionAttempts] = useState(connectionAttemptCount);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isReconnectingRef = useRef<boolean>(false);
  const mountedRef = useRef<boolean>(false);
  
  // Debug function to display message sizes
  const logMessageSize = (type: string, data: any) => {
    console.log(`Received ${type}, size: ${JSON.stringify(data).length} bytes`);
  }
  
  // Ping the server to check connection
  const pingServer = useCallback(() => {
    if (!globalWebSocket || globalWebSocket.readyState !== WebSocket.OPEN) {
      console.log('Cannot ping - socket not connected');
      return;
    }
    
    try {
      fetch('/api/ping')
        .then(response => response.json())
        .then(data => console.log('Server ping response:', data))
        .catch(error => console.error('Server ping failed:', error));
    } catch (error) {
      console.error('Error pinging server:', error);
    }
  }, []);

  // Create a WebSocket connection that persists across renders
  const connectWebSocket = useCallback(() => {
    // If we already have an open connection, just return it
    if (globalWebSocket && globalWebSocket.readyState === WebSocket.OPEN) {
      console.log('Reusing existing global WebSocket connection');
      setIsConnected(true);
      return globalWebSocket;
    }
    
    // If connection is in progress, don't start another one
    if (connectionInProgress) {
      console.log('Connection already in progress, waiting...');
      return globalWebSocket;
    }
    
    // If we have a connecting socket, just wait for it
    if (globalWebSocket && globalWebSocket.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket already connecting, waiting...');
      return globalWebSocket;
    }
    
    // Close any existing socket with issues
    if (globalWebSocket && globalWebSocket.readyState >= WebSocket.CLOSING) {
      console.log('Cleaning up existing socket');
      try {
        // Don't trigger the onclose handler when we're deliberately closing
        globalWebSocket.onclose = null;
        globalWebSocket.close();
      } catch (e) {
        console.error('Error closing existing socket:', e);
      }
      globalWebSocket = null;
    }
    
    connectionInProgress = true;
    connectionAttemptCount++;
    setConnectionAttempts(connectionAttemptCount);
    
    console.log(`Creating new WebSocket connection (attempt #${connectionAttemptCount})`);
    const hostname = window.location.hostname;
    const port = 8080;
    
    try {
      const ws = new WebSocket(`ws://${hostname}:${port}/ws/browser`);
      globalWebSocket = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        connectionInProgress = false;
        connectionAttemptCount = 0;
        setConnectionAttempts(0);
      };
      
      ws.onclose = (event) => {
        console.log(`WebSocket disconnected (code: ${event.code}, reason: ${event.reason || 'No reason provided'})`);
        setIsConnected(false);
        connectionInProgress = false;
        
        // Only attempt to reconnect if:
        // 1. Not a normal closure
        // 2. We don't already have a reconnection scheduled
        // 3. Component is still mounted
        if (event.code !== 1000 && !reconnectTimeoutRef.current && mountedRef.current) {
          const reconnectDelay = Math.min(30000, (connectionAttemptCount + 1) * 2000);
          console.log(`Scheduling reconnect in ${reconnectDelay}ms (attempt ${connectionAttemptCount})`);
          
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Reconnect timeout fired, attempting to reconnect...');
            reconnectTimeoutRef.current = null;
            
            if (mountedRef.current) {
              connectWebSocket();
            }
          }, reconnectDelay);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Don't set isConnected=false here, let the onclose handler do that
        
        // Don't show error message on every connection error
        if (connectionAttemptCount > 2 && mountedRef.current) {
          setMessages((prev) => [
            ...prev,
            {
              id: uuidv4(),
              content: `Error: Connection failed after multiple attempts. Check server status.`,
              type: 'agent',
              timestamp: Date.now(),
            },
          ]);
          setIsLoading(false);
          setHasError(true);
        }
      };
      
      ws.onmessage = (event) => {
        try {
          console.log(`Received message of size: ${event.data.length} bytes`);
          
          // Validate the message is JSON
          let data: WebSocketUpdate;
          try {
            data = JSON.parse(event.data) as WebSocketUpdate;
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
            console.error('Raw message:', event.data);
            return;
          }
          
          if (!mountedRef.current) {
            console.log('Component unmounted, ignoring message');
            return;
          }
          
          console.log(`Message type: ${data.type}`);
          
          // Ignore ping messages from server
          if (data.type === 'ping') {
            console.log('Received ping from server');
            return;
          }
          
          // Handle connection confirmation
          if (data.type === 'status' && data.status === 'Connected') {
            console.log('Received connection confirmation');
            setIsConnected(true);
            return;
          }
          
          // Update the last message time
          setLastUpdateTime(Date.now());
          
          switch (data.type) {
            case 'screenshot':
              logMessageSize('screenshot', data);
              console.log(`Screenshot data length: ${data.image_data.length}`);
              if (data.image_data && data.image_data.length > 0) {
                const newScreenshot = {
                  imageData: data.image_data,
                  timestamp: data.timestamp,
                };
                
                console.log('Setting new screenshot with data length:', data.image_data.length);
                setScreenshot(newScreenshot);
                console.log('Screenshot state explicitly set:', newScreenshot);
                
                // Clear error state if we got a valid screenshot
                setHasError(false);
                console.log('Screenshot state updated');
                
                // Force React to recognize state changed by using a small timeout
                setTimeout(() => {
                  if (!mountedRef.current) return;
                  
                  const imgElement = document.querySelector('.screenshot-container img') as HTMLImageElement;
                  if (imgElement) {
                    console.log('Screenshot element found in DOM, src length:', imgElement.src.length);
                  } else {
                    console.warn('Screenshot element not found in DOM after update');
                  }
                }, 100);
              } else {
                console.error('Received empty screenshot data');
              }
              break;
              
            case 'message':
              logMessageSize('message', data);
              setMessages((prev) => [
                ...prev,
                {
                  id: uuidv4(),
                  content: data.content,
                  type: 'agent',
                  timestamp: data.timestamp,
                },
              ]);
              break;
              
            case 'status':
              logMessageSize('status', data);
              setStatus({
                status: data.status,
                timestamp: data.timestamp,
              });
              
              if (data.status === 'Task completed') {
                setIsLoading(false);
              }
              break;
              
            case 'error':
              logMessageSize('error', data);
              setMessages((prev) => [
                ...prev,
                {
                  id: uuidv4(),
                  content: `Error: ${data.message}`,
                  type: 'agent',
                  timestamp: data.timestamp,
                },
              ]);
              setIsLoading(false);
              setHasError(true);
              break;
            
            case 'action':
              logMessageSize('action', data);
              // Log the action but don't update UI state
              console.log(`Action: ${data.action}`, data.details);
              break;
            
            default:
              console.warn(`Unknown message type: ${(data as any).type}`);
          }
        } catch (error) {
          console.error('Error processing message:', error);
          console.error('Raw message:', event.data);
          if (mountedRef.current) {
            setMessages((prev) => [
              ...prev,
              {
                id: uuidv4(),
                content: `Error: Failed to process response from server.`,
                type: 'agent',
                timestamp: Date.now(),
              },
            ]);
            setIsLoading(false);
            setHasError(true);
          }
        }
      };
      
      return ws;
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      connectionInProgress = false;
      return null;
    }
  }, []);

  // Initialize connection and set up ping interval
  useEffect(() => {
    // Set mounted flag
    mountedRef.current = true;
    
    // Connect only once on component mount
    if (!globalWebSocket || globalWebSocket.readyState > WebSocket.OPEN) {
      const connectionDelay = connectionAttemptCount === 0 ? 0 : Math.min(5000, connectionAttemptCount * 1000);
      
      setTimeout(() => {
        if (mountedRef.current) {
          console.log('Component mounted, initiating connection');
          connectWebSocket();
        }
      }, connectionDelay);
    } else if (globalWebSocket.readyState === WebSocket.OPEN) {
      // Update UI state if connection exists
      setIsConnected(true);
    }
    
    // Set up ping interval
    const pingInterval = setInterval(pingServer, 30000);
    
    // Cleanup function
    return () => {
      // Mark component as unmounted
      mountedRef.current = false;
      
      // Clear all timers
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      clearInterval(pingInterval);
      
      // Note: We're NOT closing the WebSocket here because:
      // 1. React StrictMode causes double mount/unmount in development
      // 2. We want the connection to persist across hot module reloads
      // 3. The server has a cleanup task for idle connections
      
      console.log('Component unmounted, WebSocket connection preserved');
    };
  }, [connectWebSocket, pingServer]);

  const handleSubmitTask = useCallback(
    (task: BrowsingTask) => {
      // Reset error state
      setHasError(false);
      
      // Reset screenshot state
      setScreenshot(null);
      
      // Ensure we have a connection
      if (!globalWebSocket || globalWebSocket.readyState !== WebSocket.OPEN) {
        console.log('No active connection, reconnecting...');
        connectWebSocket();
        
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            content: 'Connecting to server...',
            type: 'agent',
            timestamp: Date.now(),
          },
        ]);
        
        setTimeout(() => {
          // Retry the submission after a delay
          if (globalWebSocket && globalWebSocket.readyState === WebSocket.OPEN) {
            handleSubmitTask(task);
          } else {
            setMessages((prev) => [
              ...prev,
              {
                id: uuidv4(),
                content: 'Error: Could not connect to server. Please try again.',
                type: 'agent',
                timestamp: Date.now(),
              },
            ]);
          }
        }, 2000);
        
        return;
      }
      
      // Add user message
      const userMessage: ChatMessage = {
        id: uuidv4(),
        content: `URL: ${task.url}\nTask: ${task.instruction}`,
        type: 'user',
        timestamp: Date.now(),
      };
      
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      
      // Send task to WebSocket
      try {
        globalWebSocket.send(JSON.stringify(task));
        console.log('Task sent to server:', task);
      } catch (error) {
        console.error('Error sending task:', error);
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            content: `Error: Could not send task to server. Please try again.`,
            type: 'agent',
            timestamp: Date.now(),
          },
        ]);
        setIsLoading(false);
      }
    },
    [connectWebSocket]
  );

  // Display a debug info section in development
  const renderDebugInfo = () => {
    if (process.env.NODE_ENV !== 'development') return null;
    
    const wsState = globalWebSocket 
      ? ['Connecting', 'Open', 'Closing', 'Closed'][globalWebSocket.readyState] 
      : 'None';
    
    return (
      <div className="fixed bottom-0 right-0 bg-gray-800 text-white p-2 text-xs rounded-tl-md max-w-md opacity-70 hover:opacity-100">
        <div>Connection: {isConnected ? '✅' : '❌'}</div>
        <div>Last update: {lastUpdateTime ? new Date(lastUpdateTime).toLocaleTimeString() : 'None'}</div>
        <div>Screenshot size: {screenshot?.imageData.length ?? 0} chars</div>
        <div>Reconnect attempts: {connectionAttempts}</div>
        <div>WebSocket state: {wsState}</div>
        <div>Reconnecting: {isReconnectingRef.current ? 'Yes' : 'No'}</div>
        <div>Component mounted: {mountedRef.current ? 'Yes' : 'No'}</div>
        <div>Connection in progress: {connectionInProgress ? 'Yes' : 'No'}</div>
        <div>WebSocket ID: {globalWebSocket ? `${globalWebSocket.url}-${Date.now()}` : 'None'}</div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <h1 className="text-xl font-bold text-gray-900">AI Web Browsing Agent</h1>
          {!isConnected && (
            <div className="text-sm text-red-600 mt-1">
              Not connected to server. {connectionAttempts > 0 && `Reconnect attempt: ${connectionAttempts}`}
            </div>
          )}
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left column - Chat */}
          <div className="bg-white shadow rounded-lg overflow-hidden flex flex-col h-[calc(100vh-150px)]">
            <div className="flex-1 overflow-hidden">
              <Chat messages={messages} status={status} />
            </div>
            <div className="p-4 border-t border-gray-200">
              <TaskInput onSubmit={handleSubmitTask} isLoading={isLoading} disabled={!isConnected} />
            </div>
          </div>
          
          {/* Right column - Screenshot */}
          <div className="bg-white shadow rounded-lg overflow-hidden h-[calc(100vh-150px)]">
            <Screenshot screenshot={screenshot} hasError={hasError} />
          </div>
        </div>
      </main>
      
      {renderDebugInfo()}
    </div>
  );
} 