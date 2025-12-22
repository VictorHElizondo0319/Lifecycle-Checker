"""
SQLAlchemy Models for Machines and Parts
"""
from sqlalchemy import Column, Integer, String, Text, DECIMAL, Date, TIMESTAMP, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Machine(Base):
    """Machine/Equipment Model"""
    __tablename__ = 'machines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String(255), nullable=False, unique=True, comment='Unique equipment identifier')
    equipment_alias = Column(String(255), comment='Equipment alias/name')
    machine_description = Column(Text, comment='Machine description')
    plant = Column(String(255), comment='Plant location')
    group_responsibility = Column(String(255), comment='Group responsible for the machine')
    eam_equipment_id = Column(String(255), comment='EAM equipment ID')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationship: Many-to-Many with Parts
    parts = relationship('Part', secondary='machine_parts', back_populates='machines', lazy='dynamic')

    def __repr__(self):
        return f"<Machine(equipment_id='{self.equipment_id}', alias='{self.equipment_alias}')>"


class Part(Base):
    """Part Model"""
    __tablename__ = 'parts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Basic Part Information
    part_manufacturer = Column(String(255), nullable=False, comment='Part manufacturer name')
    manufacturer_part_number = Column(String(255), nullable=False, comment='Manufacturer part number')
    part_description = Column(Text, comment='Part description')
    part_number_ai_modified = Column(String(255), comment='AI modified part number')
    qty_on_machine = Column(DECIMAL(10, 2), default=0, comment='Quantity on machine')
    suggested_supplier = Column(String(255), comment='Suggested supplier')
    supplier_part_number = Column(String(255), comment='Supplier part number')
    gore_stock_number = Column(String(255), comment='Gore stock number')
    is_part_likely_to_fail = Column(String(50), comment='Is part likely to fail?')
    will_failures_stop_machine = Column(String(50), comment='Will failures stop machine?')
    stocking_decision = Column(String(255), comment='Stocking decision')
    min_qty_to_stock = Column(DECIMAL(10, 2), comment='Minimum quantity to stock')
    part_preplacement_line_number = Column(String(255), comment='Part preplacement line number')
    notes = Column(Text, comment='General notes')
    
    # AI Analysis Fields
    ai_status = Column(String(50), comment='AI Status: Active, Obsolete, Review')
    notes_by_ai = Column(Text, comment='Notes by AI')
    ai_confidence = Column(String(50), comment='AI Confidence: High, Medium, Low')
    ai_confidence_confirmed = Column(String(50), comment='AI Confidence Confirmed')
    
    # Replacement Information
    recommended_replacement = Column(String(255), comment='Recommended replacement part number')
    replacement_manufacturer = Column(String(255), comment='Replacement manufacturer')
    replacement_price = Column(DECIMAL(10, 2), comment='Replacement price')
    replacement_currency = Column(String(10), comment='Replacement currency (USD, EUR, etc.)')
    replacement_source_type = Column(String(255), comment='Replacement source type')
    replacement_source_url = Column(Text, comment='Replacement source URL')
    replacement_notes = Column(Text, comment='Replacement notes')
    replacement_confidence = Column(String(50), comment='Replacement confidence')
    
    # Team Notes
    will_notes = Column(Text, comment='Will notes')
    nejat_notes = Column(Text, comment='Nejat notes')
    kc_notes = Column(Text, comment='KC notes')
    ricky_notes = Column(Text, comment='Ricky notes')
    stephanie_notes = Column(Text, comment='Stephanie notes')
    pit_notes = Column(Text, comment='PIT notes')
    
    # Communication
    initial_email_communication = Column(Text, comment='Initial email communication')
    follow_up_email_communication_date = Column(Date, comment='Follow up email communication date')
    
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationship: Many-to-Many with Machines
    machines = relationship('Machine', secondary='machine_parts', back_populates='parts', lazy='dynamic')

    # Unique constraint on manufacturer + part number
    __table_args__ = (
        UniqueConstraint('part_manufacturer', 'manufacturer_part_number', name='unique_part'),
        Index('idx_manufacturer', 'part_manufacturer'),
        Index('idx_part_number', 'manufacturer_part_number'),
        Index('idx_ai_status', 'ai_status'),
    )

    def __repr__(self):
        return f"<Part(manufacturer='{self.part_manufacturer}', part_number='{self.manufacturer_part_number}')>"


class MachinePart(Base):
    """Junction Table for Many-to-Many relationship between Machines and Parts"""
    __tablename__ = 'machine_parts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey('machines.id', ondelete='CASCADE'), nullable=False)
    part_id = Column(Integer, ForeignKey('parts.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(DECIMAL(10, 2), default=1, comment='Quantity of this part used in the machine')
    cspl_line_number = Column(String(255), comment='CSPL line number')
    original_order = Column(String(255), comment='Original order')
    parent_folder = Column(String(255), comment='Parent folder')
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    machine = relationship('Machine', backref='machine_part_associations')
    part = relationship('Part', backref='machine_part_associations')

    # Unique constraint: one part can only be associated once per machine
    __table_args__ = (
        UniqueConstraint('machine_id', 'part_id', name='unique_machine_part'),
        Index('idx_machine_id', 'machine_id'),
        Index('idx_part_id', 'part_id'),
    )

    def __repr__(self):
        return f"<MachinePart(machine_id={self.machine_id}, part_id={self.part_id}, quantity={self.quantity})>"


class AnalysisLog(Base):
    """Analysis Log Model - Tracks all analysis operations"""
    __tablename__ = 'analysis_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_type = Column(String(50), nullable=False, comment='Type of analysis: product_analysis, replacement_finding')
    status = Column(String(50), nullable=False, comment='Status: in_progress, completed, failed')
    conversation_id = Column(String(255), comment='Azure AI conversation/thread ID')
    
    # Input/Output data stored as JSON
    input_data = Column(JSON, comment='Input data (products analyzed)')
    output_data = Column(JSON, comment='Output data (analysis results)')
    
    # Metadata
    products_count = Column(Integer, default=0, comment='Number of products analyzed')
    duration_seconds = Column(DECIMAL(10, 2), comment='Duration of analysis in seconds')
    error_message = Column(Text, comment='Error message if analysis failed')
    
    # Additional metadata
    user_agent = Column(String(500), comment='User agent from request')
    ip_address = Column(String(45), comment='IP address of the requester')
    
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Indexes for common queries
    __table_args__ = (
        Index('idx_analysis_type', 'analysis_type'),
        Index('idx_status', 'status'),
        Index('idx_conversation_id', 'conversation_id'),
        Index('idx_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<AnalysisLog(id={self.id}, type='{self.analysis_type}', status='{self.status}', products={self.products_count})>"

