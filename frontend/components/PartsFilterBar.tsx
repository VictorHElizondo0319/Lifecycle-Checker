'use client';

import { useState, useEffect } from 'react';
import { Part, Machine } from '@/lib/api';

interface PartsFilterBarProps {
  parts: Part[];
  machines: Machine[];
  onFilterChange: (filteredParts: Part[]) => void;
}

export default function PartsFilterBar({ parts, machines, onFilterChange }: PartsFilterBarProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedManufacturer, setSelectedManufacturer] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedMachine, setSelectedMachine] = useState('');

  // Get unique manufacturers and statuses
  const manufacturers = Array.from(
    new Set(
      parts
        .map((p) => p.part_manufacturer)
        .filter((m) => m && m !== '-')
    )
  ).sort();

  const statuses = Array.from(
    new Set(
      parts
        .map((p) => p.ai_status)
        .filter((s) => s && s !== '-')
    )
  ).sort();

  // Apply filters whenever filters or parts change
  useEffect(() => {
    let filtered = [...parts];

    // Text search across multiple fields
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((part) => {
        const searchableText = [
          part.part_manufacturer,
          part.manufacturer_part_number,
          part.part_description,
          part.notes,
          part.notes_by_ai,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return searchableText.includes(term);
      });
    }

    // Manufacturer filter
    if (selectedManufacturer) {
      filtered = filtered.filter(
        (part) => part.part_manufacturer === selectedManufacturer
      );
    }

    // Status filter
    if (selectedStatus) {
      filtered = filtered.filter((part) => part.ai_status === selectedStatus);
    }

    // Machine filter
    if (selectedMachine) {
      const machineId = parseInt(selectedMachine);
      filtered = filtered.filter((part) => {
        return part.machines?.some((m) => m.id === machineId);
      });
    }

    onFilterChange(filtered);
  }, [searchTerm, selectedManufacturer, selectedStatus, selectedMachine, parts, onFilterChange]);

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedManufacturer('');
    setSelectedStatus('');
    setSelectedMachine('');
  };

  return (
    <div className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        {/* Search */}
        <div className="md:col-span-2">
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Search
          </label>
          <div className="relative">
            <input
              type="text"
              placeholder="Search by part number, manufacturer, description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 pl-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <svg
              className="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Manufacturer Filter */}
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Manufacturer
          </label>
          <select
            value={selectedManufacturer}
            onChange={(e) => setSelectedManufacturer(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Manufacturers</option>
            {manufacturers.map((mfg) => (
              <option key={mfg} value={mfg}>
                {mfg}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            AI Status
          </label>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        {/* Machine Filter */}
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Machine
          </label>
          <select
            value={selectedMachine}
            onChange={(e) => setSelectedMachine(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Machines</option>
            {machines.map((machine) => (
              <option key={machine.id} value={machine.id.toString()}>
                {machine.equipment_id} {machine.equipment_alias ? `(${machine.equipment_alias})` : ''} ({machine.parts_count} parts)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Clear Filters */}
      {(searchTerm || selectedManufacturer || selectedStatus || selectedMachine) && (
        <div className="mt-3 flex items-center justify-end">
          <button
            onClick={clearFilters}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Clear all filters
          </button>
        </div>
      )}
    </div>
  );
}

