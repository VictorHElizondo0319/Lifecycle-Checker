'use client';

import { Product } from '@/types';
import { FIELD_CONFIGS } from '@/lib/fieldConfig';

interface TableRowProps {
  product: Product;
  visibleFields: Set<string>;
}

// Integer fields that should not show .0
const INTEGER_FIELDS = new Set([
  'original_order',
  'machine_equipment_number',
  'equipment_number',
  'equipment_alias',
  'cspl_line_number',
  'qty_on_machine',
  'gore_stock_number',
]);

// Helper function to format integer values (remove .0)
const formatIntegerValue = (value: string): string => {
  if (!value || value === '' || value === '-') return value;
  try {
    const num = parseFloat(value);
    if (!isNaN(num) && num % 1 === 0) {
      return Math.floor(num).toString();
    }
  } catch {
    // If parsing fails, return original value
  }
  return value;
};

const renderFieldValue = (product: Product, fieldKey: string) => {
  let value = product[fieldKey as keyof Product] as string | undefined;
  
  // Format integer fields to remove .0
  if (value && INTEGER_FIELDS.has(fieldKey)) {
    value = formatIntegerValue(value);
  }
  
  const displayValue = value && value !== '' ? value : '-';

  // Special formatting for certain fields
  if (fieldKey === 'ai_status' && value && value !== '-') {
    return (
      <span
        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
          value === 'Active'
            ? 'bg-green-100 text-green-800'
            : value === '🔴 Obsolete' || value.includes('Obsolete')
            ? 'bg-red-100 text-red-800'
            : 'bg-yellow-100 text-yellow-800'
        }`}
      >
        {value}
      </span>
    );
  }

  if (fieldKey === 'ai_confidence' && value && value !== '-') {
    return (
      <span
        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
          value === 'High'
            ? 'bg-green-100 text-green-800'
            : value === 'Medium'
            ? 'bg-yellow-100 text-yellow-800'
            : 'bg-red-100 text-red-800'
        }`}
      >
        {value}
      </span>
    );
  }

  // Long text fields with scrollable containers
  const longTextFields = [
    'machine_description',
    'part_description',
    'notes',
    'notes_by_ai',
    'will_notes',
    'nejat_notes',
    'kc_notes',
    'ricky_notes',
    'stephanie_notes',
    'pit_notes',
  ];

  if (longTextFields.includes(fieldKey)) {
    return (
      <div className="max-h-20 max-w-xs overflow-y-auto">
        {displayValue}
      </div>
    );
  }

  // Numeric fields - right align
  const numericFields = ['qty_on_machine', 'min_qty_to_stock'];
  if (numericFields.includes(fieldKey)) {
    return <span className="text-right">{displayValue}</span>;
  }

  return displayValue;
};

export default function TableRow({ product, visibleFields }: TableRowProps) {
  const visibleFieldConfigs = FIELD_CONFIGS.filter((field) => visibleFields.has(field.key));

  return (
    <tr className="hover:bg-gray-50">
      {visibleFieldConfigs.map((field) => {
        const isNumeric = ['qty_on_machine', 'min_qty_to_stock'].includes(field.key);
        const isLongText = [
          'machine_description',
          'part_description',
          'notes',
          'notes_by_ai',
          'will_notes',
          'nejat_notes',
          'kc_notes',
          'ricky_notes',
          'stephanie_notes',
          'pit_notes',
        ].includes(field.key);

        return (
          <td
            key={field.key}
            className={`px-3 py-2 text-sm text-gray-900 ${
              isNumeric ? 'text-right' : ''
            } ${isLongText ? '' : 'whitespace-nowrap'}`}
          >
            {renderFieldValue(product, field.key)}
          </td>
        );
      })}
    </tr>
  );
}
