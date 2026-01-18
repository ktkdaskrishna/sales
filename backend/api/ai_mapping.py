"""
AI-Powered Field Mapping Service
Uses LLM to intelligently suggest field mappings between source and target schemas
"""

import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/ai-mapping", tags=["AI Field Mapping"])

# Request/Response Models
class SourceField(BaseModel):
    name: str
    type: Optional[str] = "string"
    sample_value: Optional[str] = None
    description: Optional[str] = None

class TargetField(BaseModel):
    name: str
    type: Optional[str] = "string"
    required: bool = False
    description: Optional[str] = None

class MappingSuggestion(BaseModel):
    source_field: str
    target_field: str
    confidence: float  # 0.0 to 1.0
    reasoning: str

class AutoMappingRequest(BaseModel):
    source_name: str  # e.g., "Salesforce", "Odoo", "HubSpot"
    entity_type: str  # e.g., "contacts", "accounts", "opportunities"
    source_fields: List[SourceField]
    target_fields: Optional[List[TargetField]] = None

class AutoMappingResponse(BaseModel):
    source: str
    entity: str
    suggestions: List[MappingSuggestion]
    unmapped_source: List[str]
    unmapped_target: List[str]

# Canonical schema definitions
CANONICAL_SCHEMAS = {
    "contacts": [
        {"name": "_source_id", "type": "string", "required": True, "description": "Unique identifier from source system"},
        {"name": "name", "type": "string", "required": True, "description": "Full name of the contact"},
        {"name": "first_name", "type": "string", "required": False, "description": "First/given name"},
        {"name": "last_name", "type": "string", "required": False, "description": "Last/family name"},
        {"name": "email", "type": "string", "required": False, "description": "Email address"},
        {"name": "phone", "type": "string", "required": False, "description": "Phone number"},
        {"name": "mobile", "type": "string", "required": False, "description": "Mobile phone number"},
        {"name": "job_title", "type": "string", "required": False, "description": "Job title or position"},
        {"name": "department", "type": "string", "required": False, "description": "Department name"},
        {"name": "company_name", "type": "string", "required": False, "description": "Company or organization name"},
        {"name": "account_id", "type": "string", "required": False, "description": "Link to parent account"},
        {"name": "address", "type": "string", "required": False, "description": "Street address"},
        {"name": "city", "type": "string", "required": False, "description": "City"},
        {"name": "state", "type": "string", "required": False, "description": "State or province"},
        {"name": "country", "type": "string", "required": False, "description": "Country"},
        {"name": "postal_code", "type": "string", "required": False, "description": "Postal/ZIP code"},
    ],
    "accounts": [
        {"name": "_source_id", "type": "string", "required": True, "description": "Unique identifier from source system"},
        {"name": "name", "type": "string", "required": True, "description": "Company/account name"},
        {"name": "industry", "type": "string", "required": False, "description": "Industry classification"},
        {"name": "website", "type": "string", "required": False, "description": "Company website URL"},
        {"name": "phone", "type": "string", "required": False, "description": "Main phone number"},
        {"name": "annual_revenue", "type": "number", "required": False, "description": "Annual revenue"},
        {"name": "employee_count", "type": "integer", "required": False, "description": "Number of employees"},
        {"name": "address", "type": "string", "required": False, "description": "Street address"},
        {"name": "city", "type": "string", "required": False, "description": "City"},
        {"name": "state", "type": "string", "required": False, "description": "State or province"},
        {"name": "country", "type": "string", "required": False, "description": "Country"},
        {"name": "description", "type": "string", "required": False, "description": "Account description"},
    ],
    "opportunities": [
        {"name": "_source_id", "type": "string", "required": True, "description": "Unique identifier from source system"},
        {"name": "name", "type": "string", "required": True, "description": "Opportunity name"},
        {"name": "account_id", "type": "string", "required": False, "description": "Link to account"},
        {"name": "value", "type": "number", "required": False, "description": "Deal value/amount"},
        {"name": "stage", "type": "string", "required": False, "description": "Sales stage"},
        {"name": "probability", "type": "number", "required": False, "description": "Win probability percentage"},
        {"name": "expected_close_date", "type": "date", "required": False, "description": "Expected close date"},
        {"name": "description", "type": "string", "required": False, "description": "Opportunity description"},
        {"name": "owner_id", "type": "string", "required": False, "description": "Sales owner/rep ID"},
        {"name": "source", "type": "string", "required": False, "description": "Lead source"},
    ],
    "activities": [
        {"name": "_source_id", "type": "string", "required": True, "description": "Unique identifier from source system"},
        {"name": "type", "type": "string", "required": True, "description": "Activity type (call, meeting, email, task)"},
        {"name": "subject", "type": "string", "required": True, "description": "Activity subject/title"},
        {"name": "description", "type": "string", "required": False, "description": "Activity description"},
        {"name": "status", "type": "string", "required": False, "description": "Activity status"},
        {"name": "due_date", "type": "date", "required": False, "description": "Due date"},
        {"name": "completed_date", "type": "date", "required": False, "description": "Completion date"},
        {"name": "account_id", "type": "string", "required": False, "description": "Related account"},
        {"name": "contact_id", "type": "string", "required": False, "description": "Related contact"},
        {"name": "opportunity_id", "type": "string", "required": False, "description": "Related opportunity"},
    ],
}


async def get_ai_mapping_suggestions(
    source_name: str,
    entity_type: str,
    source_fields: List[SourceField],
    target_fields: List[TargetField]
) -> List[MappingSuggestion]:
    """Use AI to suggest field mappings - Now uses centralized LLM Service"""
    
    try:
        from services.llm_service import LLMService
        
        # Build the prompt
        source_fields_str = "\n".join([
            f"  - {f.name} ({f.type}){': ' + f.sample_value if f.sample_value else ''}"
            for f in source_fields
        ])
        
        target_fields_str = "\n".join([
            f"  - {f.name} ({f.type}, {'required' if f.required else 'optional'}): {f.description or 'No description'}"
            for f in target_fields
        ])
        
        prompt = f"""You are a data integration expert. Analyze the source fields from {source_name} and suggest the best mapping to our canonical {entity_type} schema.

SOURCE FIELDS ({source_name} - {entity_type}):
{source_fields_str}

TARGET CANONICAL SCHEMA ({entity_type}):
{target_fields_str}

For each source field, suggest the best target field mapping. Return a JSON array with objects containing:
- source_field: the source field name
- target_field: the suggested target field name (or null if no good match)
- confidence: a number from 0.0 to 1.0 indicating mapping confidence
- reasoning: brief explanation for the mapping

Consider:
1. Field name similarity (e.g., "Email" → "email")
2. Data type compatibility
3. Semantic meaning (e.g., "Amount" → "value" for opportunities)
4. Common CRM conventions

Return ONLY valid JSON array, no other text."""

        # Call centralized LLM Service
        response = await LLMService.call_llm(
            feature="field_mapping",
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000
        )
        
        # Parse the response
        # Clean up response - remove markdown code blocks if present
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        mappings = json.loads(response_text)
        
        suggestions = []
        for m in mappings:
            if m.get("target_field"):
                suggestions.append(MappingSuggestion(
                    source_field=m["source_field"],
                    target_field=m["target_field"],
                    confidence=float(m.get("confidence", 0.8)),
                    reasoning=m.get("reasoning", "AI suggested mapping")
                ))
        
        return suggestions
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response: {e}")
        # Fallback to rule-based mapping
        return get_rule_based_mappings(source_fields, target_fields)
    except Exception as e:
        print(f"AI mapping error: {e}")
        # Fallback to rule-based mapping
        return get_rule_based_mappings(source_fields, target_fields)


def get_rule_based_mappings(
    source_fields: List[SourceField],
    target_fields: List[TargetField]
) -> List[MappingSuggestion]:
    """Fallback rule-based mapping when AI is unavailable"""
    
    # Common field name mappings
    COMMON_MAPPINGS = {
        # ID fields
        "id": "_source_id", "Id": "_source_id", "ID": "_source_id",
        "hs_object_id": "_source_id", "partner_id": "_source_id",
        
        # Name fields
        "name": "name", "Name": "name", "displayName": "name",
        "firstname": "first_name", "FirstName": "first_name", "first_name": "first_name",
        "lastname": "last_name", "LastName": "last_name", "last_name": "last_name",
        
        # Contact fields
        "email": "email", "Email": "email", "mail": "email",
        "phone": "phone", "Phone": "phone", "telephone": "phone",
        "mobile": "mobile", "MobilePhone": "mobile", "mobilePhone": "mobile",
        "jobtitle": "job_title", "Title": "job_title", "title": "job_title", "JobTitle": "job_title",
        "department": "department", "Department": "department",
        
        # Company fields
        "company": "company_name", "Company": "company_name", "AccountName": "company_name",
        "industry": "industry", "Industry": "industry",
        "website": "website", "Website": "website", "domain": "website",
        "annualrevenue": "annual_revenue", "AnnualRevenue": "annual_revenue",
        "numberofemployees": "employee_count", "NumberOfEmployees": "employee_count",
        
        # Address fields
        "street": "address", "Street": "address", "BillingStreet": "address",
        "city": "city", "City": "city", "BillingCity": "city",
        "state": "state", "State": "state", "BillingState": "state",
        "country": "country", "Country": "country", "BillingCountry": "country",
        "postalcode": "postal_code", "PostalCode": "postal_code", "zip": "postal_code",
        
        # Opportunity fields
        "amount": "value", "Amount": "value", "expected_revenue": "value",
        "stagename": "stage", "StageName": "stage", "stage_id": "stage",
        "probability": "probability", "Probability": "probability",
        "closedate": "expected_close_date", "CloseDate": "expected_close_date",
        "date_deadline": "expected_close_date",
        
        # Activity fields
        "subject": "subject", "Subject": "subject",
        "description": "description", "Description": "description",
        "status": "status", "Status": "status",
        "duedate": "due_date", "ActivityDate": "due_date",
    }
    
    target_names = {f.name for f in target_fields}
    suggestions = []
    
    for sf in source_fields:
        source_lower = sf.name.lower().replace("_", "").replace("-", "")
        
        # Try direct mapping
        if sf.name in COMMON_MAPPINGS:
            target = COMMON_MAPPINGS[sf.name]
            if target in target_names:
                suggestions.append(MappingSuggestion(
                    source_field=sf.name,
                    target_field=target,
                    confidence=0.95,
                    reasoning="Direct field name match"
                ))
                continue
        
        # Try lowercase match
        for target in target_names:
            target_lower = target.lower().replace("_", "")
            if source_lower == target_lower or source_lower in target_lower or target_lower in source_lower:
                suggestions.append(MappingSuggestion(
                    source_field=sf.name,
                    target_field=target,
                    confidence=0.8,
                    reasoning="Field name similarity match"
                ))
                break
    
    return suggestions


@router.post("/suggest", response_model=AutoMappingResponse)
async def suggest_field_mappings(request: AutoMappingRequest):
    """
    Use AI to suggest intelligent field mappings between source and canonical schema
    """
    # Get target schema
    entity_type = request.entity_type.lower()
    if entity_type not in CANONICAL_SCHEMAS:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
    
    target_fields = [TargetField(**f) for f in CANONICAL_SCHEMAS[entity_type]]
    
    if request.target_fields:
        target_fields = request.target_fields
    
    # Get AI suggestions
    suggestions = await get_ai_mapping_suggestions(
        request.source_name,
        request.entity_type,
        request.source_fields,
        target_fields
    )
    
    # Find unmapped fields
    mapped_sources = {s.source_field for s in suggestions}
    mapped_targets = {s.target_field for s in suggestions}
    
    unmapped_source = [f.name for f in request.source_fields if f.name not in mapped_sources]
    unmapped_target = [f.name for f in target_fields if f.name not in mapped_targets]
    
    return AutoMappingResponse(
        source=request.source_name,
        entity=request.entity_type,
        suggestions=suggestions,
        unmapped_source=unmapped_source,
        unmapped_target=unmapped_target
    )


@router.get("/canonical-schema/{entity_type}")
async def get_canonical_schema(entity_type: str):
    """Get the canonical schema for an entity type"""
    entity_type = entity_type.lower()
    if entity_type not in CANONICAL_SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Unknown entity type: {entity_type}")
    
    return {
        "entity_type": entity_type,
        "fields": CANONICAL_SCHEMAS[entity_type]
    }


@router.get("/canonical-schemas")
async def list_canonical_schemas():
    """List all available canonical schemas"""
    return {
        "schemas": list(CANONICAL_SCHEMAS.keys()),
        "details": {k: len(v) for k, v in CANONICAL_SCHEMAS.items()}
    }
