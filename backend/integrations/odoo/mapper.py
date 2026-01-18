"""
Odoo Data Mappers
Transform Odoo data to canonical models
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging

from sync_engine.base_components import BaseMapper
from core.base import RawRecord
from core.enums import IntegrationSource, EntityType, Priority, OpportunityStage, ActivityType, ActivityStatus
from data_lake.models import (
    CanonicalContact,
    CanonicalAccount,
    CanonicalOpportunity,
    CanonicalActivity,
    CanonicalUser,
)


logger = logging.getLogger(__name__)


class OdooContactMapper(BaseMapper):
    """Maps Odoo res.partner (contacts) to CanonicalContact"""
    
    def __init__(self, field_mappings: Optional[Dict[str, str]] = None):
        super().__init__(IntegrationSource.ODOO, field_mappings)
    
    def map_to_canonical(self, raw_record: RawRecord) -> CanonicalContact:
        """Transform raw Odoo partner to canonical contact"""
        data = raw_record.raw_data
        
        # Extract related field values (Odoo returns tuples for many2one)
        state = self._extract_m2o_name(data.get('state_id'))
        country = self._extract_m2o_name(data.get('country_id'))
        owner_id = self._extract_m2o_id(data.get('user_id'))
        team_id = self._extract_m2o_id(data.get('team_id'))
        account_id = self._extract_m2o_id(data.get('parent_id'))
        
        contact = CanonicalContact(
            name=data.get('name', ''),
            email=data.get('email') or None,
            phone=data.get('phone') or None,
            mobile=data.get('mobile') or None,
            
            # Company association
            account_id=str(account_id) if account_id else None,
            company_name=self._extract_m2o_name(data.get('parent_id')),
            job_title=data.get('function') or None,
            
            # Address
            street=data.get('street') or None,
            city=data.get('city') or None,
            state=state,
            country=country,
            postal_code=data.get('zip') or None,
            
            # Classification
            contact_type='customer',  # Default, could be enhanced
            tags=self._extract_tag_names(data.get('category_id', [])),
            
            # Ownership
            owner_id=str(owner_id) if owner_id else None,
            team_id=str(team_id) if team_id else None,
            
            # Status
            is_active=data.get('active', True),
            notes=data.get('comment') or None,
        )
        
        # Add source reference
        contact.add_source(
            source=IntegrationSource.ODOO.value,
            source_id=str(data.get('id')),
            source_model='res.partner'
        )
        
        # Set timestamps from Odoo
        if data.get('create_date'):
            contact.created_at = self._parse_odoo_datetime(data['create_date'])
        if data.get('write_date'):
            contact.updated_at = self._parse_odoo_datetime(data['write_date'])
        
        return contact
    
    def _extract_m2o_id(self, value: Any) -> Optional[int]:
        """Extract ID from many2one field (tuple or False)"""
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            return value[0]
        elif isinstance(value, int):
            return value
        return None
    
    def _extract_m2o_name(self, value: Any) -> Optional[str]:
        """Extract name from many2one field"""
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return value[1]
        return None
    
    def _extract_tag_names(self, value: Any) -> list:
        """Extract tag names from many2many field"""
        if isinstance(value, list):
            return [str(v) for v in value]  # IDs for now, could fetch names
        return []
    
    def _parse_odoo_datetime(self, value: str) -> datetime:
        """Parse Odoo datetime string"""
        try:
            if 'T' in value:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except:
            return datetime.now(timezone.utc)


class OdooAccountMapper(BaseMapper):
    """Maps Odoo res.partner (companies) to CanonicalAccount"""
    
    def __init__(self, field_mappings: Optional[Dict[str, str]] = None):
        super().__init__(IntegrationSource.ODOO, field_mappings)
    
    def map_to_canonical(self, raw_record: RawRecord) -> CanonicalAccount:
        """Transform raw Odoo company to canonical account"""
        data = raw_record.raw_data
        
        state = self._extract_m2o_name(data.get('state_id'))
        country = self._extract_m2o_name(data.get('country_id'))
        owner_id = self._extract_m2o_id(data.get('user_id'))
        team_id = self._extract_m2o_id(data.get('team_id'))
        industry = self._extract_m2o_name(data.get('industry_id'))
        
        account = CanonicalAccount(
            name=data.get('name', ''),
            website=data.get('website') or None,
            industry=industry,
            employee_count=data.get('employee') if isinstance(data.get('employee'), int) else None,
            
            # Address
            street=data.get('street') or None,
            city=data.get('city') or None,
            state=state,
            country=country,
            postal_code=data.get('zip') or None,
            
            # Classification
            account_type='customer',
            tags=self._extract_tag_names(data.get('category_id', [])),
            
            # Ownership
            owner_id=str(owner_id) if owner_id else None,
            team_id=str(team_id) if team_id else None,
            
            # Status
            is_active=data.get('active', True),
        )
        
        account.add_source(
            source=IntegrationSource.ODOO.value,
            source_id=str(data.get('id')),
            source_model='res.partner'
        )
        
        return account
    
    def _extract_m2o_id(self, value: Any) -> Optional[int]:
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            return value[0]
        elif isinstance(value, int):
            return value
        return None
    
    def _extract_m2o_name(self, value: Any) -> Optional[str]:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return value[1]
        return None
    
    def _extract_tag_names(self, value: Any) -> list:
        if isinstance(value, list):
            return [str(v) for v in value]
        return []


class OdooOpportunityMapper(BaseMapper):
    """Maps Odoo crm.lead to CanonicalOpportunity"""
    
    # Odoo stage to canonical stage mapping
    STAGE_MAP = {
        'new': OpportunityStage.LEAD,
        'qualified': OpportunityStage.QUALIFICATION,
        'proposition': OpportunityStage.PROPOSAL,
        'won': OpportunityStage.CLOSED_WON,
        'lost': OpportunityStage.CLOSED_LOST,
    }
    
    def __init__(self, field_mappings: Optional[Dict[str, str]] = None):
        super().__init__(IntegrationSource.ODOO, field_mappings)
    
    def map_to_canonical(self, raw_record: RawRecord) -> CanonicalOpportunity:
        """Transform raw Odoo lead to canonical opportunity"""
        data = raw_record.raw_data
        
        owner_id = self._extract_m2o_id(data.get('user_id'))
        team_id = self._extract_m2o_id(data.get('team_id'))
        partner_id = self._extract_m2o_id(data.get('partner_id'))
        stage_name = self._extract_m2o_name(data.get('stage_id'))
        
        # Map stage
        stage = self._map_stage(stage_name, data.get('won_status'))
        
        # Map priority
        priority = self._map_priority(data.get('priority', '1'))
        
        opportunity = CanonicalOpportunity(
            name=data.get('name', ''),
            account_id=str(partner_id) if partner_id else None,
            
            # Deal info
            stage=stage.value,
            probability=int(data.get('probability', 0)),
            amount=float(data.get('expected_revenue', 0) or 0),
            
            # Dates
            expected_close_date=self._parse_date(data.get('date_deadline')),
            actual_close_date=self._parse_date(data.get('date_closed')),
            
            # Classification
            opportunity_type='new_business' if data.get('type') == 'opportunity' else 'lead',
            priority=priority,
            tags=self._extract_tag_ids(data.get('tag_ids', [])),
            
            # Ownership
            owner_id=str(owner_id) if owner_id else None,
            team_id=str(team_id) if team_id else None,
            
            # Status
            is_closed=stage in (OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST),
            is_won=stage == OpportunityStage.CLOSED_WON,
            
            # Loss reason
            loss_reason=self._extract_m2o_name(data.get('lost_reason_id')),
        )
        
        opportunity.add_source(
            source=IntegrationSource.ODOO.value,
            source_id=str(data.get('id')),
            source_model='crm.lead'
        )
        
        return opportunity
    
    def _map_stage(self, stage_name: Optional[str], won_status: Any) -> OpportunityStage:
        """Map Odoo stage to canonical stage"""
        if not stage_name:
            return OpportunityStage.LEAD
        
        stage_lower = stage_name.lower()
        
        # Check won/lost status first
        if won_status == 'won':
            return OpportunityStage.CLOSED_WON
        if won_status == 'lost':
            return OpportunityStage.CLOSED_LOST
        
        # Map by stage name
        for key, canonical_stage in self.STAGE_MAP.items():
            if key in stage_lower:
                return canonical_stage
        
        # Default mapping by keywords
        if 'qualify' in stage_lower or 'qualif' in stage_lower:
            return OpportunityStage.QUALIFICATION
        if 'propos' in stage_lower or 'quote' in stage_lower:
            return OpportunityStage.PROPOSAL
        if 'negoti' in stage_lower:
            return OpportunityStage.NEGOTIATION
        if 'discov' in stage_lower:
            return OpportunityStage.DISCOVERY
        
        return OpportunityStage.LEAD
    
    def _map_priority(self, priority: str) -> Priority:
        """Map Odoo priority to canonical priority"""
        mapping = {
            '0': Priority.LOW,
            '1': Priority.MEDIUM,
            '2': Priority.HIGH,
            '3': Priority.CRITICAL,
        }
        return mapping.get(str(priority), Priority.MEDIUM)
    
    def _extract_m2o_id(self, value: Any) -> Optional[int]:
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            return value[0]
        elif isinstance(value, int):
            return value
        return None
    
    def _extract_m2o_name(self, value: Any) -> Optional[str]:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return value[1]
        return None
    
    def _extract_tag_ids(self, value: Any) -> list:
        if isinstance(value, list):
            return [str(v) for v in value]
        return []
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            if isinstance(value, str):
                if 'T' in value:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            pass
        return None


class OdooActivityMapper(BaseMapper):
    """Maps Odoo mail.activity to CanonicalActivity"""
    
    ACTIVITY_TYPE_MAP = {
        'email': ActivityType.EMAIL,
        'call': ActivityType.CALL,
        'meeting': ActivityType.MEETING,
        'todo': ActivityType.TASK,
        'upload_file': ActivityType.TASK,
    }
    
    def __init__(self, field_mappings: Optional[Dict[str, str]] = None):
        super().__init__(IntegrationSource.ODOO, field_mappings)
    
    def map_to_canonical(self, raw_record: RawRecord) -> CanonicalActivity:
        """Transform raw Odoo activity to canonical activity"""
        data = raw_record.raw_data
        
        owner_id = self._extract_m2o_id(data.get('user_id'))
        activity_type_name = self._extract_m2o_name(data.get('activity_type_id'))
        
        # Map activity type
        activity_type = self._map_activity_type(activity_type_name)
        
        # Map status
        status = self._map_status(data.get('state'))
        
        activity = CanonicalActivity(
            subject=data.get('summary') or data.get('name', 'Activity'),
            activity_type=activity_type,
            description=data.get('note') or None,
            
            # Timing
            due_date=self._parse_date(data.get('date_deadline')),
            
            # Status
            status=status,
            
            # Ownership
            owner_id=str(owner_id) if owner_id else None,
            assigned_to=str(owner_id) if owner_id else None,
        )
        
        # Try to link to related record
        res_model = data.get('res_model')
        res_id = data.get('res_id')
        if res_model == 'res.partner' and res_id:
            activity.account_id = str(res_id)
        elif res_model == 'crm.lead' and res_id:
            activity.opportunity_id = str(res_id)
        
        activity.add_source(
            source=IntegrationSource.ODOO.value,
            source_id=str(data.get('id')),
            source_model='mail.activity'
        )
        
        return activity
    
    def _map_activity_type(self, type_name: Optional[str]) -> ActivityType:
        if not type_name:
            return ActivityType.TASK
        
        type_lower = type_name.lower()
        for key, activity_type in self.ACTIVITY_TYPE_MAP.items():
            if key in type_lower:
                return activity_type
        
        return ActivityType.TASK
    
    def _map_status(self, state: Optional[str]) -> ActivityStatus:
        if state == 'done':
            return ActivityStatus.COMPLETED
        if state == 'cancel':
            return ActivityStatus.CANCELLED
        if state == 'overdue':
            return ActivityStatus.OVERDUE
        return ActivityStatus.PENDING
    
    def _extract_m2o_id(self, value: Any) -> Optional[int]:
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            return value[0]
        elif isinstance(value, int):
            return value
        return None
    
    def _extract_m2o_name(self, value: Any) -> Optional[str]:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return value[1]
        return None
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            if isinstance(value, str):
                return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            pass
        return None


class OdooUserMapper(BaseMapper):
    """Maps Odoo res.users to CanonicalUser"""
    
    def __init__(self, field_mappings: Optional[Dict[str, str]] = None):
        super().__init__(IntegrationSource.ODOO, field_mappings)
    
    def map_to_canonical(self, raw_record: RawRecord) -> CanonicalUser:
        """Transform raw Odoo user to canonical user"""
        from core.enums import UserRole
        
        data = raw_record.raw_data
        
        user = CanonicalUser(
            email=data.get('login') or data.get('email', ''),
            name=data.get('name', ''),
            
            # Auth
            auth_provider='odoo',
            external_id=str(data.get('id')),
            
            # Role (default, can be overridden)
            role=UserRole.SALES_REP,
            
            # Status
            is_active=data.get('active', True),
        )
        
        user.add_source(
            source=IntegrationSource.ODOO.value,
            source_id=str(data.get('id')),
            source_model='res.users'
        )
        
        return user
    
    def _extract_m2o_id(self, value: Any) -> Optional[int]:
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            return value[0]
        elif isinstance(value, int):
            return value
        return None



class OdooInvoiceMapper(BaseMapper):
    """Maps Odoo account.move (invoices) to canonical invoice format"""
    
    def __init__(self, field_mappings: Optional[Dict[str, str]] = None):
        super().__init__(IntegrationSource.ODOO, field_mappings)
    
    def map_to_canonical(self, raw_record: RawRecord) -> Dict[str, Any]:
        """Transform raw Odoo invoice to canonical format"""
        data = raw_record.raw_data
        
        # Extract many2one fields (Odoo returns [id, "name"] tuples)
        partner_id = self._extract_m2o_id(data.get('partner_id'))
        partner_name = self._extract_m2o_name(data.get('partner_id'))
        user_id = self._extract_m2o_id(data.get('invoice_user_id'))
        salesperson_name = self._extract_m2o_name(data.get('invoice_user_id'))
        
        # Map Odoo invoice states to standard statuses
        state_mapping = {
            'draft': 'draft',
            'posted': 'posted',
            'cancel': 'cancelled',
            'paid': 'paid'
        }
        status = state_mapping.get(data.get('state', 'draft'), 'draft')
        
        # Build canonical invoice (dict format - no CanonicalInvoice model yet)
        invoice = {
            'source_id': str(data.get('id')),  # CRITICAL: Always string for MongoDB
            'invoice_number': data.get('name', ''),
            'customer_id': str(partner_id) if partner_id else None,
            'customer_name': partner_name,
            'total_amount': float(data.get('amount_total', 0)),
            'amount_due': float(data.get('amount_residual', 0)),
            'status': status,
            'invoice_date': data.get('invoice_date'),
            'due_date': data.get('invoice_date_due'),
            'salesperson_id': str(user_id) if user_id else None,
            'salesperson_name': salesperson_name,
            'currency': self._extract_m2o_name(data.get('currency_id')) or 'USD',
            'payment_state': data.get('payment_state'),
            'move_type': data.get('move_type', 'out_invoice'),
            
            # Metadata
            'created_at': data.get('create_date'),
            'updated_at': data.get('write_date'),
        }
        
        return invoice
    
    def _extract_m2o_id(self, value: Any) -> Optional[int]:
        """Extract ID from many2one field [id, name]"""
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            return value[0]
        elif isinstance(value, int):
            return value
        return None
    
    def _extract_m2o_name(self, value: Any) -> Optional[str]:
        """Extract name from many2one field [id, name]"""
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return str(value[1])
        elif isinstance(value, str):
            return value
        return None

