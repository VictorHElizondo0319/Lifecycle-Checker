'use client';

import {useSafeRouter, useSafePathname, isStaticExport} from '@/hooks/useSafeRouter';
import Link from 'next/link';
import AzureStatus from './AzureStatus';

export default function Sidebar() {
  const pathname = useSafePathname();
  const isStatic = isStaticExport();

  const isActive = (path: string, pageKey: string) => {
    if (isStatic) {
      // In Electron mode, paths are like "critical.html" or "/critical.html"
      // Extract the page name from both current pathname and target path
      const currentPage = pathname.replace(/^\//, '').replace(/\.html$/, '') || 'critical';
      const targetPage = path.replace(/^\//, '').replace(/\.html$/, '') || pageKey;
      
      // Also check the pageKey directly
      return currentPage === targetPage || currentPage === pageKey;
    } else {
      // In web mode, use standard Next.js pathname matching
      return pathname === path || pathname?.startsWith(path + '/');
    }
  };

  const pages = [
    {
      label: "Critical Separate Parts",
      path: useSafeRouter("critical"),
      key: "critical"
    },
    {
      label: "All Parts",
      path: useSafeRouter("parts"),
      key: "parts"
    }
  ]

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
        {pages.map((page) => {
          const active = isActive(page.path, page.key);
          return (
            <Link href={page.path} 
            className={`block w-full rounded-lg px-4 py-3 text-left text-sm font-medium transition-colors ${
              active
                ? 'bg-purple-100 text-purple-700 border-2 border-purple-300'
                : 'bg-gray-50 text-gray-700 border-2 border-transparent hover:bg-gray-100'
            }`}
            key={page.key || page.path}>
              {page.label}
            </Link>
          );
        })}
      </div>

      {/* Azure Status Section */}
      <div className="border-t border-gray-200 p-4">
        <AzureStatus />
      </div>
    </div>
  );
}

