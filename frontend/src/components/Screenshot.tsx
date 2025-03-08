import React, { useEffect } from 'react';
import { ScreenshotData } from '@/types';

interface ScreenshotProps {
  screenshot: ScreenshotData | null;
  hasError?: boolean;
}

const Screenshot: React.FC<ScreenshotProps> = ({ screenshot, hasError = false }) => {
  useEffect(() => {
    if (screenshot) {
      console.log('Screenshot component received new data:', screenshot);
      console.log('Attempting to render image with data length:', screenshot.imageData.length);
    }
  }, [screenshot]);

  return (
    <div className="screenshot-container">
      {screenshot ? (
        <img
          src={`data:image/jpeg;base64,${screenshot.imageData}`}
          alt="Current webpage view"
          className="rounded-lg"
        />
      ) : (
        <div className="flex flex-col items-center justify-center text-gray-500">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-24 w-24 mb-4 ${hasError ? 'text-red-400' : 'text-gray-400'}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            {hasError ? (
              // Error icon
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            ) : (
              // Monitor icon
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            )}
          </svg>
          <p className="text-lg">
            {hasError 
              ? "Unable to capture webpage screenshot" 
              : "No screenshot available"}
          </p>
          <p className="text-sm mt-2">
            {hasError
              ? "Try a website with less security restrictions"
              : "Enter a URL and task to start browsing"}
          </p>
          {hasError && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 max-w-md">
              <p className="font-semibold">Recommended websites for testing:</p>
              <ul className="list-disc list-inside mt-1">
                <li>wikipedia.org</li>
                <li>github.com</li>
                <li>nytimes.com</li>
                <li>weather.gov</li>
                <li>mozilla.org</li>
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Screenshot; 