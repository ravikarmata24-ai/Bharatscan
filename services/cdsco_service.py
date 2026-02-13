import requests
from config import Config


class CDSCOService:
    """
    Service to interact with CDSCO (Central Drugs Standard Control Organisation)
    
    CDSCO is the national regulatory body for pharmaceuticals and medical devices in India.
    
    Note: CDSCO doesn't have a fully public product lookup API.
    This service provides:
    1. Drug schedule classification
    2. Known medicine database
    3. Banned drug checking
    4. Generic medicine alternatives
    """

    # Drug schedules under Drugs and Cosmetics Act, 1940
    DRUG_SCHEDULES = {
        'H': {
            'name': 'Schedule H',
            'description': 'Prescription drugs - Can only be sold on prescription of a Registered Medical Practitioner',
            'label_requirement': 'Rx symbol and "Schedule H Drug - Warning: To be sold by retail on the prescription of a Registered Medical Practitioner only"',
        },
        'H1': {
            'name': 'Schedule H1',
            'description': 'Restricted prescription drugs - Requires maintaining records of sale',
            'label_requirement': 'Rx symbol and "Schedule H1 Drug" with additional record-keeping',
            'examples': ['Alprazolam', 'Codeine', 'Diazepam', 'Tramadol'],
        },
        'X': {
            'name': 'Schedule X',
            'description': 'Narcotics and psychotropic substances - Strictest control',
            'label_requirement': 'XRx symbol - Requires prescription in duplicate',
            'examples': ['Amphetamine', 'Barbiturates', 'Ketamine'],
        },
        'G': {
            'name': 'Schedule G',
            'description': 'Drugs that require caution label',
            'label_requirement': '"Caution: It is dangerous to take this preparation except under medical supervision"',
        },
        'OTC': {
            'name': 'Over The Counter',
            'description': 'Can be sold without prescription',
            'label_requirement': 'No prescription warning required',
        },
    }

    # Known Indian generic medicines database (sample)
    GENERIC_MEDICINES = {
        'paracetamol_500': {
            'generic_name': 'Paracetamol',
            'strength': '500mg',
            'brands': [
                {'name': 'Crocin', 'manufacturer': 'GSK', 'mrp': 33.51},
                {'name': 'Calpol', 'manufacturer': 'GSK', 'mrp': 30.00},
                {'name': 'Dolo', 'manufacturer': 'Micro Labs', 'mrp': 30.00},
                {'name': 'P-500', 'manufacturer': 'Cadila', 'mrp': 10.50},
                {'name': 'Pyrigesic', 'manufacturer': 'East India', 'mrp': 8.50},
            ],
            'jan_aushadhi_available': True,
            'jan_aushadhi_price': 6.70,
            'schedule': 'OTC',
        },
        'paracetamol_650': {
            'generic_name': 'Paracetamol',
            'strength': '650mg',
            'brands': [
                {'name': 'Dolo 650', 'manufacturer': 'Micro Labs', 'mrp': 33.62},
                {'name': 'Crocin 650', 'manufacturer': 'GSK', 'mrp': 35.00},
                {'name': 'Calpol 650', 'manufacturer': 'GSK', 'mrp': 32.00},
            ],
            'jan_aushadhi_available': True,
            'jan_aushadhi_price': 8.40,
            'schedule': 'OTC',
        },
        'azithromycin_500': {
            'generic_name': 'Azithromycin',
            'strength': '500mg',
            'brands': [
                {'name': 'Azithral', 'manufacturer': 'Alembic', 'mrp': 103.00},
                {'name': 'Zithromax', 'manufacturer': 'Pfizer', 'mrp': 120.00},
                {'name': 'Azee', 'manufacturer': 'Cipla', 'mrp': 95.00},
                {'name': 'ATM', 'manufacturer': 'Lupin', 'mrp': 85.00},
            ],
            'jan_aushadhi_available': True,
            'jan_aushadhi_price': 22.26,
            'schedule': 'H',
        },
        'amoxicillin_500': {
            'generic_name': 'Amoxicillin',
            'strength': '500mg',
            'brands': [
                {'name': 'Mox', 'manufacturer': 'Ranbaxy', 'mrp': 85.00},
                {'name': 'Amoxil', 'manufacturer': 'GSK', 'mrp': 90.00},
                {'name': 'Novamox', 'manufacturer': 'Cipla', 'mrp': 78.00},
            ],
            'jan_aushadhi_available': True,
            'jan_aushadhi_price': 12.30,
            'schedule': 'H',
        },
        'omeprazole_20': {
            'generic_name': 'Omeprazole',
            'strength': '20mg',
            'brands': [
                {'name': 'Omez', 'manufacturer': 'Dr. Reddys', 'mrp': 75.00},
                {'name': 'Ocid', 'manufacturer': 'Zydus', 'mrp': 70.00},
                {'name': 'Prilosec', 'manufacturer': 'AstraZeneca', 'mrp': 95.00},
            ],
            'jan_aushadhi_available': True,
            'jan_aushadhi_price': 5.00,
            'schedule': 'H',
        },
    }

    # Banned drugs in India (as per CDSCO)
    BANNED_DRUGS = [
        {
            'name': 'Nimesulide (for children under 12)',
            'notification': 'GSR 82(E), 2011',
            'reason': 'Hepatotoxicity in children',
        },
        {
            'name': 'Cisapride',
            'notification': 'GSR 160(E), 2011',
            'reason': 'Cardiac arrhythmia risk',
        },
        {
            'name': 'Phenylpropanolamine',
            'notification': 'GSR 407(E), 2011',
            'reason': 'Risk of haemorrhagic stroke',
        },
        {
            'name': 'Rosiglitazone',
            'notification': 'GSR 529(E), 2010',
            'reason': 'Cardiovascular risk',
        },
        {
            'name': 'Sibutramine',
            'notification': 'GSR 935(E), 2010',
            'reason': 'Cardiovascular events',
        },
        {
            'name': 'Gatifloxacin (oral formulation)',
            'notification': 'GSR 791(E), 2011',
            'reason': 'Dysglycemia risk',
        },
        {
            'name': 'Tegaserod',
            'notification': 'GSR 72(E), 2011',
            'reason': 'Cardiovascular events',
        },
        {
            'name': 'Dextropropoxyphene',
            'notification': 'GSR 578(E), 2013',
            'reason': 'Fatal overdose risk, cardiac toxicity',
        },
        {
            'name': 'Pioglitazone (in some formulations)',
            'notification': 'Under review',
            'reason': 'Bladder cancer risk',
        },
    ]

    # Fixed Dose Combinations banned in India
    BANNED_FDCS = [
        'Nimesulide + Paracetamol (for children)',
        'Pholcodine + Promethazine',
        'Analgin + combination products',
        'Ofloxacin + Ornidazole (certain formulations)',
        'Cough syrups with codeine (for children)',
    ]

    def __init__(self):
        self.base_url = Config.CDSCO_API_BASE
        self.session = requests.Session()

    def search_medicine(self, barcode):
        """
        Search for medicine by barcode
        Note: CDSCO doesn't have a direct barcode API
        Returns None to fall through to other services
        """
        try:
            # Placeholder for future CDSCO API integration
            return None
        except Exception as e:
            print(f"CDSCO search error: {e}")
            return None

    def get_drug_schedule(self, schedule_code):
        """Get drug schedule information"""
        return self.DRUG_SCHEDULES.get(schedule_code.upper(), None)

    def check_banned_drug(self, composition):
        """Check if a drug composition contains banned substances"""
        if not composition:
            return []

        warnings = []
        composition_lower = composition.lower()

        for drug in self.BANNED_DRUGS:
            drug_name = drug['name'].split('(')[0].strip().lower()
            if drug_name in composition_lower:
                warnings.append({
                    'type': 'banned_drug',
                    'severity': 'critical',
                    'drug': drug['name'],
                    'notification': drug['notification'],
                    'reason': drug['reason'],
                    'message': f"⛔ {drug['name']} is BANNED in India. Notification: {drug['notification']}",
                })

        return warnings

    def find_generic_alternatives(self, brand_name=None, composition=None):
        """
        Find cheaper generic alternatives and Jan Aushadhi options
        
        Jan Aushadhi: Indian government's scheme for affordable generic medicines
        """
        alternatives = []

        search_term = (brand_name or '').lower()
        composition_term = (composition or '').lower()

        for key, medicine in self.GENERIC_MEDICINES.items():
            # Search by brand name
            brand_match = any(
                search_term in brand['name'].lower()
                for brand in medicine['brands']
            )
            # Search by composition
            comp_match = medicine['generic_name'].lower() in composition_term

            if brand_match or comp_match:
                alternatives.append({
                    'generic_name': medicine['generic_name'],
                    'strength': medicine['strength'],
                    'brands': sorted(medicine['brands'], key=lambda x: x['mrp']),
                    'cheapest_brand': min(medicine['brands'], key=lambda x: x['mrp']),
                    'most_expensive': max(medicine['brands'], key=lambda x: x['mrp']),
                    'jan_aushadhi_available': medicine.get('jan_aushadhi_available', False),
                    'jan_aushadhi_price': medicine.get('jan_aushadhi_price'),
                    'potential_savings': self._calculate_savings(medicine),
                    'schedule': medicine.get('schedule', 'Unknown'),
                })

        return alternatives

    def _calculate_savings(self, medicine):
        """Calculate potential savings with generic/Jan Aushadhi"""
        if not medicine.get('jan_aushadhi_available'):
            return None

        most_expensive = max(brand['mrp'] for brand in medicine['brands'])
        jan_price = medicine.get('jan_aushadhi_price', 0)

        if jan_price > 0 and most_expensive > 0:
            savings_percent = ((most_expensive - jan_price) / most_expensive) * 100
            return {
                'branded_price': most_expensive,
                'jan_aushadhi_price': jan_price,
                'savings_amount': round(most_expensive - jan_price, 2),
                'savings_percent': round(savings_percent, 1),
            }
        return None

    def get_drug_interactions(self, compositions):
        """
        Check for known drug interactions
        Note: This is a simplified version. Use actual medical databases in production.
        """
        known_interactions = {
            ('paracetamol', 'warfarin'): {
                'severity': 'moderate',
                'description': 'Paracetamol may enhance the anticoagulant effect of Warfarin',
            },
            ('azithromycin', 'warfarin'): {
                'severity': 'major',
                'description': 'Azithromycin may increase Warfarin levels, increasing bleeding risk',
            },
            ('omeprazole', 'clopidogrel'): {
                'severity': 'major',
                'description': 'Omeprazole may reduce the effectiveness of Clopidogrel',
            },
            ('metformin', 'alcohol'): {
                'severity': 'major',
                'description': 'Risk of lactic acidosis increases with alcohol use',
            },
        }

        interactions = []
        comp_lower = [c.lower().strip() for c in compositions]

        for (drug1, drug2), info in known_interactions.items():
            if drug1 in ' '.join(comp_lower) and drug2 in ' '.join(comp_lower):
                interactions.append({
                    'drugs': f"{drug1} + {drug2}",
                    'severity': info['severity'],
                    'description': info['description'],
                })

        return interactions

    def verify_drug_license(self, license_number):
        """Verify drug manufacturing/sales license"""
        result = {
            'license_number': license_number,
            'format_valid': False,
            'message': '',
        }

        if not license_number:
            result['message'] = 'No license number provided'
            return result

        # Indian drug license format patterns
        # Manufacturing: State/Number/Year (e.g., KTK/28/113/2006)
        # Sales: State/Number (e.g., MH/15234)
        import re

        # Manufacturing license pattern
        mfg_pattern = r'^[A-Z]{1,3}/\d+/\d+/\d{4}$'
        # Simple license pattern
        simple_pattern = r'^[A-Z]{1,3}[-/]\d+$'

        if re.match(mfg_pattern, license_number):
            result['format_valid'] = True
            result['license_type'] = 'Manufacturing License'
            parts = license_number.split('/')
            result['state_code'] = parts[0]
            result['year'] = parts[-1]
        elif re.match(simple_pattern, license_number):
            result['format_valid'] = True
            result['license_type'] = 'Drug License'
        else:
            result['message'] = 'Unrecognized license format'

        return result