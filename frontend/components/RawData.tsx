'use client';

export default function RawData() {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-800">Raw Data</h1>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">Raw Data view coming soon...</p>
          <p className="mt-2 text-sm text-gray-400">
            This section will display raw data from the uploaded Excel file.
          </p>
        </div>
      </div>
    </div>
  );
}

