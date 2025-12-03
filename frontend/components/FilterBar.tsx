'use client';

import { useState, useEffect } from 'react';
import { Product } from '@/types';

interface FilterBarProps {
  products: Product[];
  onFilterChange: (filteredProducts: Product[]) => void;
}

export default function FilterBar({ products, onFilterChange }: FilterBarProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedManufacturer, setSelectedManufacturer] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  // Get unique manufacturers and statuses
  const manufacturers = Array.from(
    new Set(
      products
        .map((p) => p.part_manufacturer || p.manufacturer)
        .filter((m) => m && m !== '-')
    )
  ).sort();

  const statuses = Array.from(
    new Set(
      products
        .map((p) => p.ai_status)
        .filter((s) => s && s !== '-')
    )
  ).sort();

  // Apply filters whenever filters or products change
  useEffect(() => {
    let filtered = [...products];

    // Text search across multiple fields
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((product) => {
        const searchableText = [
          product.part_manufacturer,
          product.manufacturer_part_number,
          product.part_description,
          product.machine_equipment_number,
          product.equipment_alias,
          product.notes,
          product.notes_by_ai,
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
        (product) =>
          (product.part_manufacturer || product.manufacturer) === selectedManufacturer
      );
    }

    // Status filter
    if (selectedStatus) {
      filtered = filtered.filter((product) => product.ai_status === selectedStatus);
    }

    onFilterChange(filtered);
  }, [searchTerm, selectedManufacturer, selectedStatus, products, onFilterChange]);

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedManufacturer('');
    setSelectedStatus('');
  };

  return (
    <div className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
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
      </div>

      {/* Clear Filters */}
      {(searchTerm || selectedManufacturer || selectedStatus) && (
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

