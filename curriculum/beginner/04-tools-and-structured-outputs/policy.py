from typing import Dict, Any, Set, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, ValidationError
import logging

class ErrorResult(BaseModel):
    error_type: Literal['UNKNOWN_TOOL', 'SCHEMA_ERROR', 'AUTH_ERROR', 'BUSINESS_ERROR', 'INTERNAL_TOOL_ERROR']
    message: str

class ExecutionContext(BaseModel):
    tenant_id: str
    roles: List[str]

class OrderResult(BaseModel):
    order_id: str
    tenant_id: str
    customer_id: str
    total_cents: int
    status: str

class RefundResult(BaseModel):
    status: str
    transaction_id: str
    amount_cents: int
    order_id: str

class GetOrderArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    order_id: str = Field(..., description='The exact order ID (e.g. ORD-123)')

RefundReason = Literal['damaged', 'wrong_item', 'late_delivery', 'customer_dissatisfied']

class IssueRefundArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    order_id: str = Field(..., description='The exact order ID to refund')
    amount_cents: int = Field(..., description='The amount to refund in cents')
    reason: RefundReason = Field(..., description='Approved reason category for the refund')
    idempotency_key: str = Field(..., description='Unique client idempotency token to prevent duplicate refund executions')

DB_ORDERS: Dict[str, Dict[str, Any]] = {
    'ORD-123': {'tenant_id': 'northstar', 'customer_id': 'CUST-101', 'total_cents': 5000, 'status': 'delivered'},
    'ORD-456': {'tenant_id': 'northstar', 'customer_id': 'CUST-202', 'total_cents': 10000, 'status': 'delivered'},
    'ORD-789': {'tenant_id': 'other_tenant', 'customer_id': 'CUST-999', 'total_cents': 7500, 'status': 'delivered'}
}
DB_PROCESSED_REFUNDS: Set[str] = set()

def get_order_impl(args: GetOrderArgs) -> OrderResult:
    rec = DB_ORDERS[args.order_id]
    return OrderResult(
        order_id=args.order_id,
        tenant_id=rec['tenant_id'],
        customer_id=rec['customer_id'],
        total_cents=rec['total_cents'],
        status=rec['status']
    )

def issue_refund_impl(args: IssueRefundArgs) -> RefundResult:
    if args.idempotency_key in DB_PROCESSED_REFUNDS:
        return RefundResult(
            status='already_processed',
            transaction_id='tx_existing_prev',
            amount_cents=args.amount_cents,
            order_id=args.order_id
        )
    DB_PROCESSED_REFUNDS.add(args.idempotency_key)
    return RefundResult(
        status='refund_issued',
        transaction_id='tx_new_8899',
        amount_cents=args.amount_cents,
        order_id=args.order_id
    )

def crashing_tool_impl(args: GetOrderArgs) -> OrderResult:
    raise RuntimeError('Database connection suddenly dropped!')

TOOL_REGISTRY = {
    'get_order': {'schema': GetOrderArgs, 'func': get_order_impl, 'effect': 'read', 'permission': 'order:read'},
    'issue_refund': {'schema': IssueRefundArgs, 'func': issue_refund_impl, 'effect': 'write', 'permission': 'refund:issue'},
    'crash_test': {'schema': GetOrderArgs, 'func': crashing_tool_impl, 'effect': 'read', 'permission': 'order:read'}
}

def dispatch_tool(tool_name: str, raw_args: str, ctx: ExecutionContext, registry: dict = TOOL_REGISTRY, db_orders: dict = DB_ORDERS) -> BaseModel:
    if tool_name not in registry:
        return ErrorResult(error_type='UNKNOWN_TOOL', message=f"Tool '{tool_name}' not found in registry.")
    
    entry = registry[tool_name]
    req_perm = entry['permission']
    if req_perm not in ctx.roles:
        return ErrorResult(error_type='AUTH_ERROR', message=f"Permission denied: Actor lacks '{req_perm}' role.")
        
    try:
        validated_args = entry['schema'].model_validate_json(raw_args)
    except ValidationError as e:
        err_msg = ', '.join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        return ErrorResult(error_type='SCHEMA_ERROR', message=err_msg)

    order_id = getattr(validated_args, 'order_id', None)
    if order_id:
        if order_id not in db_orders:
            return ErrorResult(error_type='BUSINESS_ERROR', message=f"Order '{order_id}' not found.")
        order = db_orders[order_id]
        if order['tenant_id'] != ctx.tenant_id:
            return ErrorResult(error_type='AUTH_ERROR', message='Cross-tenant access denied: order belongs to another organization.')
        if tool_name == 'issue_refund':
            if validated_args.amount_cents > order['total_cents']:
                return ErrorResult(error_type='BUSINESS_ERROR', message=f"Refund amount ({validated_args.amount_cents}¢) exceeds order total ({order['total_cents']}¢).")
            
    try:
        return entry['func'](validated_args)
    except Exception as e:
        logging.getLogger(__name__).error(f'Internal unexpected error executing {tool_name}: {e}', exc_info=True)
        return ErrorResult(error_type='INTERNAL_TOOL_ERROR', message='The tool failed unexpectedly.')
