#!/usr/bin/env python3
"""
Script to seed the contacts table with sample data based on the Smukfest 2025 shift plan.
"""

import sys
import os
from typing import List, Dict

# Add project root to sys.path to allow importing 'app' modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from app.database import SessionLocal
from app.models import Contact
from app.crud import create_contact
from app import schemas

def get_sample_contacts() -> List[Dict]:
    """Returns sample contact data based on the Smukfest 2025 shift plan."""
    return [
        # ANSL BLÅ KANAL 10
        {"category": "ANSL", "role": "Vagt Søndag 3/8", "name": "Mikkel Andersen", "phone": "23 46 43 19", "channel": "BLÅ KANAL 10", "sort_order": 1},
        {"category": "ANSL", "role": "Vagt Mandag 4/8", "name": "Birgitte Duch", "phone": "52 39 40 25", "channel": "BLÅ KANAL 10", "sort_order": 2},
        {"category": "ANSL", "role": "Vagt Tirsdag 5/8", "name": "Thomas Dissing", "phone": "23 28 69 95", "channel": "BLÅ KANAL 10", "sort_order": 3},
        {"category": "ANSL", "role": "Vagt Onsdag 6/8", "name": "Claus Valter Rohde", "phone": "42 43 02 05", "channel": "BLÅ KANAL 10", "sort_order": 4},
        {"category": "ANSL", "role": "Vagt Torsdag 7/8", "name": "Christian Fenger-Eriksen", "phone": "26 36 24 16", "channel": "BLÅ KANAL 10", "sort_order": 5},
        {"category": "ANSL", "role": "Vagt Fredag 8/8", "name": "Jesper Hedegaard", "phone": "25 30 82 60", "channel": "BLÅ KANAL 10", "sort_order": 6},
        {"category": "ANSL", "role": "Vagt Lørdag 9/8", "name": "Søren Vad Jepsen", "phone": "20 72 63 99", "channel": "BLÅ KANAL 10", "sort_order": 7},
        {"category": "ANSL", "role": "Vagt Søndag 10/8", "name": "Mads Rasmussen", "phone": "30 56 69 77", "channel": "BLÅ KANAL 10", "sort_order": 8},
        
        # BØGE STAGE SECURITY
        {"category": "BØGE STAGE SECURITY", "role": "Vagttelefon 24-7", "name": "Vagttelefon", "phone": "51 16 36 18", "channel": "BLÅ KANAL 6", "notes": "Svarer 24-7", "sort_order": 10},
        
        # BØGE STAGE MANAGER
        {"category": "BØGE STAGE MANAGER", "role": "Stage Manager 08:00-16:00", "name": "Kim Mosfelt", "phone": "26 22 22 98", "channel": "BLÅ KANAL 12", "sort_order": 11},
        {"category": "BØGE STAGE MANAGER", "role": "Stage Manager 13:00-23:00", "name": "Michael Munch", "phone": "31 17 04 00", "channel": "BLÅ KANAL 12", "sort_order": 12},
        {"category": "BØGE STAGE MANAGER", "role": "Stage Manager 20:00-08:00", "name": "Anders Tinggaard", "phone": "25 32 27 14", "channel": "BLÅ KANAL 12", "sort_order": 13},
        
        # THE HOOD STAGE SECURITY
        {"category": "THE HOOD STAGE SECURITY", "role": "Vagttelefon 24-7", "name": "Vagttelefon", "phone": "61 61 41 27", "channel": "BLÅ KANAL 2", "notes": "Svarer 24-7", "sort_order": 20},
        
        # THE HOOD STAGE MANAGER
        {"category": "THE HOOD STAGE MANAGER", "role": "Stage Manager dagtimer", "name": "Jesper Philbert", "phone": "40 45 17 25", "channel": "BLÅ KANAL 14", "sort_order": 21},
        {"category": "THE HOOD STAGE MANAGER", "role": "Stage Manager aften/nat", "name": "Kent Mejer", "phone": "20 84 37 23", "channel": "BLÅ KANAL 14", "sort_order": 22},
        
        # STJERNEN OG MÅNEN STAGE SECURITY
        {"category": "STJERNEN OG MÅNEN STAGE SECURITY", "role": "Vagt alle dage", "name": "Erik Bohn Andreasen", "phone": "27 52 11 12", "channel": "BLÅ KANAL 7", "sort_order": 30},
        {"category": "STJERNEN OG MÅNEN STAGE SECURITY", "role": "Back up", "name": "Trine Bruun Christensen", "phone": "20 44 63 43", "channel": "BLÅ KANAL 7", "sort_order": 31},
        
        # STJERNEN STAGE MANAGER
        {"category": "STJERNEN STAGE MANAGER", "role": "Stage Manager Stjernescenen", "name": "Nils Lybæk", "phone": "26 18 61 11", "channel": "BLÅ KANAL 13", "sort_order": 32},
        {"category": "STJERNEN STAGE MANAGER", "role": "Show dag production manager", "name": "Jok Østergaard", "phone": "26 20 30 20", "channel": "BLÅ KANAL 13", "sort_order": 33},
        
        # MÅNEN STAGE MANAGER
        {"category": "MÅNEN STAGE MANAGER", "role": "Stage Manager", "name": "Tarek Nielsen", "phone": "21 73 24 32", "channel": "BLÅ KANAL 14", "sort_order": 40},
        {"category": "MÅNEN STAGE MANAGER", "role": "Stage Manager", "name": "Lucas P Sørensen", "phone": "31 77 39 55", "channel": "BLÅ KANAL 14", "sort_order": 41},
        {"category": "MÅNEN STAGE MANAGER", "role": "Show dag production manager", "name": "Mathilde T Hansen", "phone": "20 42 68 96", "channel": "BLÅ KANAL 14", "sort_order": 42},
        
        # UDSIGTEN STAGE MANAGER
        {"category": "UDSIGTEN STAGE MANAGER", "role": "Stage Manager Udsigten", "name": "Emma Markvad", "phone": "51 50 81 23", "channel": None, "notes": "Kontakt gennem BSK", "sort_order": 50},
        
        # LIVE CAMP STAGE MANAGER
        {"category": "LIVE CAMP STAGE MANAGER", "role": "Sceneansvarlig & Stagemanager", "name": "Steffen Fragttrup", "phone": "40 83 12 02", "channel": "ORANGE KANAL 9", "sort_order": 60},
    ]

def seed_contacts():
    """Seeds the contacts table with sample data."""
    print("Starting contact seeding...")
    
    db = SessionLocal()
    try:
        # Check if contacts already exist
        existing_contacts = db.query(Contact).count()
        if existing_contacts > 0:
            print(f"Contacts table already has {existing_contacts} entries. Skipping seeding.")
            return
        
        sample_contacts = get_sample_contacts()
        
        print(f"Adding {len(sample_contacts)} sample contacts...")
        
        for contact_data in sample_contacts:
            # Convert to ContactCreate schema
            contact_schema = schemas.ContactCreate(
                category=contact_data["category"],
                role=contact_data["role"],
                name=contact_data["name"],
                phone=contact_data["phone"],
                channel=contact_data.get("channel"),
                notes=contact_data.get("notes"),
                sort_order=contact_data.get("sort_order", 0),
                is_active=True
            )
            
            # Create contact using CRUD function
            created_contact = create_contact(db, contact_schema)
            print(f"  ✓ Added: {created_contact.category} - {created_contact.name}")
        
        print(f"Successfully seeded {len(sample_contacts)} contacts!")
        
    except Exception as e:
        print(f"Error seeding contacts: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_contacts() 