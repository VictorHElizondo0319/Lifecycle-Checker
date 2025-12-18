import { FieldConfig } from '@/components/FieldSelector';

export const FIELD_CONFIGS: FieldConfig[] = [
  // Basic Information
  { key: 'original_order', label: 'Original Order', category: 'Basic Information' },
  { key: 'parent_folder', label: 'Parent Folder', category: 'Basic Information' },
  { key: 'machine_equipment_number', label: 'Machine Equipment Number', category: 'Basic Information' },
  { key: 'equipment_alias', label: 'Equipment Alias', category: 'Basic Information' },
  { key: 'machine_description', label: 'Machine Description', category: 'Basic Information' },
  { key: 'group_responsibility', label: 'Group Responsibility', category: 'Basic Information' },
  { key: 'plant', label: 'Plant', category: 'Basic Information' },
  { key: 'initiator', label: 'Initiator', category: 'Basic Information' },
  { key: 'cspl_line_number', label: 'CSPL Line Number', category: 'Basic Information' },
  // Part Information
  { key: 'part_description', label: 'Part Description', category: 'Part Information' },
  { key: 'part_manufacturer', label: 'Part Manufacturer', category: 'Part Information' },
  { key: 'manufacturer_part_number', label: 'Manufacturer Part #', category: 'Part Information' },
  { key: 'qty_on_machine', label: 'Qty on Machine', category: 'Part Information' },
  { key: 'suggested_supplier', label: 'Suggested Supplier', category: 'Part Information' },
  { key: 'supplier_part_number', label: 'Supplier Part Number', category: 'Part Information' },
  { key: 'gore_stock_number', label: 'Gore Stock Number', category: 'Part Information' },

  // Stocking & Failure
  { key: 'is_part_likely_to_fail', label: 'Is Part Likely to Fail?', category: 'Stocking & Failure' },
  { key: 'will_failures_stop_machine', label: 'Will Failures Stop Machine', category: 'Stocking & Failure' },
  { key: 'stocking_decision', label: 'Stocking Decision', category: 'Stocking & Failure' },
  { key: 'min_qty_to_stock', label: 'Min Qty to Stock', category: 'Stocking & Failure' },
  { key: 'part_preplacement_line_number', label: 'Part Preplacement Line #', category: 'Stocking & Failure' },

  // Notes
  { key: 'notes', label: 'Notes', category: 'Notes' },

  // AI Analysis
  { key: 'part_number_ai_modified', label: 'Part# (AI Modified)', category: 'AI Analysis' },
  { key: 'manufacturer', label: 'Manufacturer', category: 'AI Analysis' },
  { key: 'ai_status', label: 'AI Status', category: 'AI Analysis' },
  { key: 'notes_by_ai', label: 'Notes By AI', category: 'AI Analysis' },
  { key: 'ai_confidence', label: 'AI Confidence', category: 'AI Analysis' },
  { key: 'ai_confidence_confirmed', label: 'AI Confidence Confirmed', category: 'AI Analysis' },

  // Team Notes
  { key: 'will_notes', label: 'Will Notes', category: 'Team Notes' },
  { key: 'nejat_notes', label: 'Nejat Notes', category: 'Team Notes' },
  { key: 'kc_notes', label: 'KC Notes', category: 'Team Notes' },
  { key: 'ricky_notes', label: "Ricky's Notes", category: 'Team Notes' },
  { key: 'stephanie_notes', label: 'Stephanie Notes', category: 'Team Notes' },
  { key: 'pit_notes', label: 'PIT Notes', category: 'Team Notes' },

  // Communication
  { key: 'initial_email_communication', label: 'Initial Email Communication', category: 'Communication' },
  { key: 'follow_up_email_communication_date', label: 'Follow up Email Date', category: 'Communication' },

  // Replacement Information
  { key: 'recommended_replacement', label: 'Recommended Replacement', category: 'Replacement Information' },
  { key: 'replacement_manufacturer', label: 'Replacement Manufacturer', category: 'Replacement Information' },
  { key: 'replacement_price', label: 'Replacement Price', category: 'Replacement Information' },
  { key: 'replacement_currency', label: 'Replacement Currency', category: 'Replacement Information' },
  { key: 'replacement_source_type', label: 'Replacement Source Type', category: 'Replacement Information' },
  { key: 'replacement_source_url', label: 'Replacement Source URL', category: 'Replacement Information' },
  { key: 'replacement_notes', label: 'Replacement Notes', category: 'Replacement Information' },
  { key: 'replacement_confidence', label: 'Replacement Confidence', category: 'Replacement Information' },
];

// Default visible fields (most commonly used)
export const CRITICAL_DEFAULT_VISIBLE_FIELDS = new Set([
  'original_order',
  'part_description',
  'part_manufacturer',
  'manufacturer_part_number',
  'qty_on_machine',
  'ai_status',
  'notes_by_ai',
  'ai_confidence',
]);


