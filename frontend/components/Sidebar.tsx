'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (path: string) => {
    return pathname === path || pathname?.startsWith(path + '/');
  };

  return (
    <div className="flex h-screen w-64 flex-col border-r border-gray-200 bg-white">
      {/* Top Section - Icon/Avatar */}
      <div className="flex items-center justify-center border-b border-gray-200 p-6">
        <div className="relative">
          {/* Cross/Move Icon */}
          <div className="absolute -top-2 left-1/2 -translate-x-1/2">
            <svg
              className="h-4 w-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 9l4-4 4 4m0 6l-4 4-4-4"
              />
            </svg>
          </div>
          {/* Circular Avatar/Icon */}
          <div className="h-16 w-16 rounded-full border-2 border-gray-300 bg-gray-100 flex items-center justify-center">
            <svg
              className="h-8 w-8 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex-1 space-y-2 p-4">
        <Link
          href="/critical"
          className={`block w-full rounded-lg px-4 py-3 text-left text-sm font-medium transition-colors ${
            isActive('/critical')
              ? 'bg-purple-100 text-purple-700 border-2 border-purple-300'
              : 'bg-gray-50 text-gray-700 border-2 border-transparent hover:bg-gray-100'
          }`}
        >
          Critical Separate Parts
        </Link>
        <Link
          href="/raw-data"
          className={`block w-full rounded-lg px-4 py-3 text-left text-sm font-medium transition-colors ${
            isActive('/raw-data')
              ? 'bg-purple-100 text-purple-700 border-2 border-purple-300'
              : 'bg-gray-50 text-gray-700 border-2 border-transparent hover:bg-gray-100'
          }`}
        >
          Raw Data
        </Link>
      </div>
    </div>
  );
}
