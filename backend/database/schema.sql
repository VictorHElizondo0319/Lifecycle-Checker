-- MySQL Database Schema for Lifecycle Checker
-- Machines and Parts with Many-to-Many Relationship

-- Create database (uncomment if needed)
-- CREATE DATABASE IF NOT EXISTS lifecycle_checker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE lifecycle_checker;

-- Machines Table
-- Stores machine/equipment information
CREATE TABLE IF NOT EXISTS machines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id VARCHAR(255) NOT NULL UNIQUE COMMENT 'Unique equipment identifier',
    equipment_alias VARCHAR(255) COMMENT 'Equipment alias/name',
    machine_description TEXT COMMENT 'Machine description',
    plant VARCHAR(255) COMMENT 'Plant location',
    group_responsibility VARCHAR(255) COMMENT 'Group responsible for the machine',
    eam_equipment_id VARCHAR(255) COMMENT 'EAM equipment ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_equipment_id (equipment_id),
    INDEX idx_plant (plant)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Parts Table
-- Stores part information with unique constraint on manufacturer + part number
CREATE TABLE IF NOT EXISTS parts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    part_manufacturer VARCHAR(255) NOT NULL COMMENT 'Part manufacturer name',
    manufacturer_part_number VARCHAR(255) NOT NULL COMMENT 'Manufacturer part number',
    part_description TEXT COMMENT 'Part description',
    part_number_ai_modified VARCHAR(255) COMMENT 'AI modified part number',
    qty_on_machine DECIMAL(10, 2) DEFAULT 0 COMMENT 'Quantity on machine',
    suggested_supplier VARCHAR(255) COMMENT 'Suggested supplier',
    supplier_part_number VARCHAR(255) COMMENT 'Supplier part number',
    gore_stock_number VARCHAR(255) COMMENT 'Gore stock number',
    is_part_likely_to_fail VARCHAR(50) COMMENT 'Is part likely to fail?',
    will_failures_stop_machine VARCHAR(50) COMMENT 'Will failures stop machine?',
    stocking_decision VARCHAR(255) COMMENT 'Stocking decision',
    min_qty_to_stock DECIMAL(10, 2) COMMENT 'Minimum quantity to stock',
    part_preplacement_line_number VARCHAR(255) COMMENT 'Part preplacement line number',
    notes TEXT COMMENT 'General notes',
    -- AI Analysis Fields
    ai_status VARCHAR(50) COMMENT 'AI Status: Active, Obsolete, Review',
    notes_by_ai TEXT COMMENT 'Notes by AI',
    ai_confidence VARCHAR(50) COMMENT 'AI Confidence: High, Medium, Low',
    ai_confidence_confirmed VARCHAR(50) COMMENT 'AI Confidence Confirmed',
    -- Replacement Information
    recommended_replacement VARCHAR(255) COMMENT 'Recommended replacement part number',
    replacement_manufacturer VARCHAR(255) COMMENT 'Replacement manufacturer',
    replacement_price DECIMAL(10, 2) COMMENT 'Replacement price',
    replacement_currency VARCHAR(10) COMMENT 'Replacement currency (USD, EUR, etc.)',
    replacement_source_type VARCHAR(255) COMMENT 'Replacement source type',
    replacement_source_url TEXT COMMENT 'Replacement source URL',
    replacement_notes TEXT COMMENT 'Replacement notes',
    replacement_confidence VARCHAR(50) COMMENT 'Replacement confidence',
    -- Team Notes
    will_notes TEXT COMMENT 'Will notes',
    nejat_notes TEXT COMMENT 'Nejat notes',
    kc_notes TEXT COMMENT 'KC notes',
    ricky_notes TEXT COMMENT 'Ricky notes',
    stephanie_notes TEXT COMMENT 'Stephanie notes',
    pit_notes TEXT COMMENT 'PIT notes',
    -- Communication
    initial_email_communication TEXT COMMENT 'Initial email communication',
    follow_up_email_communication_date DATE COMMENT 'Follow up email communication date',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Unique constraint on manufacturer + part number combination
    UNIQUE KEY unique_part (part_manufacturer, manufacturer_part_number),
    INDEX idx_manufacturer (part_manufacturer),
    INDEX idx_part_number (manufacturer_part_number),
    INDEX idx_ai_status (ai_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Machine Parts Junction Table
-- Many-to-Many relationship between machines and parts
CREATE TABLE IF NOT EXISTS machine_parts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    machine_id INT NOT NULL,
    part_id INT NOT NULL,
    quantity DECIMAL(10, 2) DEFAULT 1 COMMENT 'Quantity of this part used in the machine',
    cspl_line_number VARCHAR(255) COMMENT 'CSPL line number',
    original_order VARCHAR(255) COMMENT 'Original order',
    parent_folder VARCHAR(255) COMMENT 'Parent folder',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Foreign keys
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE,
    -- Unique constraint: one part can only be associated once per machine
    UNIQUE KEY unique_machine_part (machine_id, part_id),
    INDEX idx_machine_id (machine_id),
    INDEX idx_part_id (part_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Analysis Logs Table
-- Tracks all analysis operations for auditing and debugging
CREATE TABLE IF NOT EXISTS analysis_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL COMMENT 'Type of analysis: product_analysis, replacement_finding',
    status VARCHAR(50) NOT NULL COMMENT 'Status: in_progress, completed, failed',
    conversation_id VARCHAR(255) COMMENT 'Azure AI conversation/thread ID',
    input_data JSON COMMENT 'Input data (products analyzed)',
    output_data JSON COMMENT 'Output data (analysis results)',
    products_count INT DEFAULT 0 COMMENT 'Number of products analyzed',
    duration_seconds DECIMAL(10, 2) COMMENT 'Duration of analysis in seconds',
    error_message TEXT COMMENT 'Error message if analysis failed',
    user_agent VARCHAR(500) COMMENT 'User agent from request',
    ip_address VARCHAR(45) COMMENT 'IP address of the requester',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_analysis_type (analysis_type),
    INDEX idx_status (status),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

