# admin_views.py
from sqladmin import ModelView
from models import Vehicle, Maintenance, Inspection, Fee, Disposal, Attachment

class VehicleAdmin(ModelView, model=Vehicle):
    name = "Vehicle"
    name_plural = "Vehicles"
    column_list = [Vehicle.plate_no, Vehicle.vehicle_type, Vehicle.make, Vehicle.model, Vehicle.year, Vehicle.status]
    column_searchable_list = [Vehicle.plate_no, Vehicle.make, Vehicle.model]

class MaintenanceAdmin(ModelView, model=Maintenance):
    name = "Maintenance"
    name_plural = "Maintenance"
    column_list = [Maintenance.vehicle_id, Maintenance.category, Maintenance.performed_on, Maintenance.amount, Maintenance.vendor]
    column_searchable_list = [Maintenance.vendor]

class InspectionAdmin(ModelView, model=Inspection):
    name = "Inspection"
    column_list = [Inspection.vehicle_id, Inspection.kind, Inspection.inspected_on, Inspection.next_due_on, Inspection.result]

class FeeAdmin(ModelView, model=Fee):
    name = "Fee"
    column_list = [Fee.vehicle_id, Fee.fee_type, Fee.period_start, Fee.period_end, Fee.amount, Fee.paid_on]

class DisposalAdmin(ModelView, model=Disposal):
    name = "Disposal"
    column_list = [Disposal.vehicle_id, Disposal.disposed_on, Disposal.reason]

class AttachmentAdmin(ModelView, model=Attachment):
    name = "Attachment"
    column_list = [Attachment.entity_type, Attachment.entity_id, Attachment.file_name, Attachment.uploaded_at]