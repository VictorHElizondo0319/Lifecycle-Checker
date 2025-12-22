# Database Schema

MySQL database schema for storing machines and parts with a many-to-many relationship.

## Database Structure

### Tables

1. **machines** - Stores machine/equipment information
   - `equipment_id` (UNIQUE) - Unique equipment identifier
   - Other machine metadata fields

2. **parts** - Stores part information
   - `part_manufacturer` + `manufacturer_part_number` (UNIQUE) - Unique part identifier
   - All part fields including AI analysis and replacement information

3. **machine_parts** - Junction table for many-to-many relationship
   - Links machines to parts
   - `machine_id` + `part_id` (UNIQUE) - Ensures one part can only be associated once per machine
   - Additional fields like quantity, cspl_line_number, etc.

## Setup

1. **Install MySQL dependencies:**
```bash
pip install -r requirements.txt
```

2. **Create MySQL database:**
```sql
CREATE DATABASE lifecycle_checker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. **Configure database connection in `.env`:**
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=lifecycle_checker
DB_CHARSET=utf8mb4
```

4. **Run schema creation:**
```bash
# Option 1: Using SQL file directly
mysql -u your_username -p lifecycle_checker < database/schema.sql

# Option 2: Using Python (creates tables via SQLAlchemy)
python -c "from database.db_config import init_db; init_db()"
```

## Usage

### Using SQLAlchemy Models

```python
from database import get_db_session, Machine, Part, MachinePart

# Get a session
with get_db_session() as session:
    # Create a machine
    machine = Machine(
        equipment_id='EQ-001',
        equipment_alias='Production Line 1',
        plant='Plant A'
    )
    session.add(machine)
    
    # Create a part
    part = Part(
        part_manufacturer='BANNER',
        manufacturer_part_number='45136',
        part_description='Sensor',
        ai_status='Active'
    )
    session.add(part)
    session.commit()
    
    # Associate part with machine
    machine_part = MachinePart(
        machine_id=machine.id,
        part_id=part.id,
        quantity=2
    )
    session.add(machine_part)
    session.commit()
    
    # Query machines with their parts
    machine = session.query(Machine).filter_by(equipment_id='EQ-001').first()
    parts = machine.parts.all()
    
    # Query parts with their machines
    part = session.query(Part).filter_by(manufacturer_part_number='45136').first()
    machines = part.machines.all()
```

## Relationships

- **Machine → Parts**: One machine can have many parts (via `machine_parts` table)
- **Part → Machines**: One part can be used in many machines (via `machine_parts` table)
- **Cascade Delete**: Deleting a machine or part will automatically remove associations in `machine_parts`

## Constraints

- `equipment_id` in `machines` table is UNIQUE
- `part_manufacturer` + `manufacturer_part_number` in `parts` table is UNIQUE
- `machine_id` + `part_id` in `machine_parts` table is UNIQUE (prevents duplicate associations)

