import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .forms import TicketCreateForm, AdminTicketForm, IssueFormFieldForm, ServiceCatalogItemForm
from .models import Ticket, IssueFormField, TicketStatus, TicketComment, TicketHistory, ServiceCatalogItem, Category
from accounts.models import UserRole, TechnicianGroup

@login_required(login_url='accounts:login')
@require_http_methods(['GET', 'POST'])
def ticket_create(request):
	issue_fields = IssueFormField.objects.filter(is_active=True).select_related('category').order_by('order', 'id')
	
	# Initial category pre-selection if passed via query string ?category=<id>
	initial_data = {}
	preselect_cat = request.GET.get('category')
	if preselect_cat:
		try:
			cat_obj = Category.objects.get(pk=preselect_cat)
			initial_data['category'] = cat_obj
			for ifield in issue_fields:
				if ifield.field_key == 'facing_issue_in' or 'facing' in ifield.field_key.lower():
					for opt in ifield.options:
						if opt.lower() in cat_obj.name.lower() or cat_obj.name.lower() in opt.lower():
							initial_data[ifield.field_key] = [opt] if ifield.field_type == IssueFormField.FieldType.CHECKBOX else opt
							break
		except (Category.DoesNotExist, ValueError):
			pass

	form = TicketCreateForm(request.POST or None, request.FILES or None, initial=initial_data, issue_fields=issue_fields)
	if request.method == 'POST' and form.is_valid():
		ticket = form.save(commit=False)
		ticket.reporter = request.user
		
		# Collect custom answers
		custom_answers = {}
		selected_cat_name = None

		for field_item in issue_fields:
			val = form.cleaned_data.get(field_item.field_key)
			if val:
				if isinstance(val, list):
					val = ", ".join(val)
				custom_answers[field_item.label] = str(val)
				if field_item.field_key == 'facing_issue_in' or 'facing' in field_item.field_key.lower():
					selected_cat_name = val

		other_details = request.POST.get('other_issue_details', '').strip()
		if other_details:
			custom_answers['Other Issue Details'] = other_details

		# If category not yet set, dynamically assign from user's chosen dynamic question option
		if not ticket.category_id:
			if selected_cat_name:
				primary_choice = selected_cat_name.split(',')[0].strip()
				cat_obj, _ = Category.objects.get_or_create(
					name=primary_choice,
					defaults={'description': f'Auto-created category from {primary_choice}'}
				)
				ticket.category = cat_obj
			else:
				default_cat, _ = Category.objects.get_or_create(name='Other', defaults={'description': 'General IT issues'})
				ticket.category = default_cat

		if ticket.category_id and 'Facing Issue In' not in custom_answers:
			custom_answers['Facing Issue In'] = ticket.category.name


		# Populate ticket.description from problem_description or custom answers or form.description
		prob_desc = (
			form.cleaned_data.get('problem_description') or 
			form.cleaned_data.get('description') or 
			custom_answers.get('Problem Description')
		)
		if prob_desc:
			ticket.description = str(prob_desc).strip()
		elif not ticket.description:
			ticket.description = ticket.title

		if not ticket.attachment and request.FILES:
			for _, fval in request.FILES.items():
				ticket.attachment = fval
				break

		ticket.custom_answers = custom_answers
		ticket.save()


		# Intelligent assignment: Auto-assign technician based on category
		ticket.assign_to_technician()

		messages.success(request, f"Ticket #{ticket.ticket_number} submitted successfully.")
		return redirect('tickets:my_tickets')


	# Build JSON schema of fields & conditions for the frontend dynamic reactive engine

	fields_schema = []
	for f in issue_fields:
		fields_schema.append({
			'key': f.field_key,
			'label': f.label,
			'type': f.field_type,
			'category_id': f.category_id if f.category_id else 'global',
			'condition_type': f.condition_type,
			'condition_field_key': f.condition_field_key,
			'condition_operator': f.condition_operator,
			'condition_value': f.condition_value,
			'options': f.options,
			'required': f.required,
			'help_text': f.help_text,
			'max_file_size_mb': f.max_file_size_mb,
		})

	max_attachment_size_mb = 5
	for f in issue_fields:
		if f.field_key == 'attachment' or f.field_type == IssueFormField.FieldType.FILE:
			max_attachment_size_mb = f.max_file_size_mb
			break

	return render(request, 'tickets/ticket_create.html', {
		'form': form,
		'issue_fields': issue_fields,
		'max_attachment_size_mb': max_attachment_size_mb,
		'fields_schema_json': json.dumps(fields_schema),
	})



@login_required(login_url='accounts:login')
@require_http_methods(['GET', 'POST'])
def issue_form_builder(request):
	if request.user.profile.role != UserRole.ADMIN or not request.user.is_staff:
		return redirect('accounts:dashboard')

	action = request.POST.get('action')
	
	# Action: Update Technician Group Routing for a Category
	if request.method == 'POST' and action == 'update_routing':
		category_id = request.POST.get('category_id')
		group_id = request.POST.get('group_id')
		if category_id:
			cat = get_object_or_404(Category, pk=category_id)
			if group_id:
				grp = get_object_or_404(TechnicianGroup, pk=group_id)
				cat.assigned_group = grp
			else:
				cat.assigned_group = None
			cat.save()
			messages.success(request, f"Routing updated: '{cat.name}' assigned to {cat.assigned_group.name if cat.assigned_group else 'General Queue'}.")
		return redirect('tickets:form_builder')

	# Action: Add / Configure Question Field
	form = IssueFormFieldForm(request.POST or None)
	if request.method == 'POST' and (not action or action == 'save_field'):
		if form.is_valid():
			saved_field = form.save()
			# If this field has options, ensure matching categories exist for routing
			if saved_field.options:
				for opt in saved_field.options:
					if opt.lower() != 'other':
						Category.objects.get_or_create(name=opt, defaults={'description': f'Auto-created category from {saved_field.label}'})
			messages.success(request, f"Question '{saved_field.label}' configured successfully.")
			return redirect('tickets:form_builder')

	fields = IssueFormField.objects.select_related('category').all().order_by('order', 'id')
	categories = Category.objects.select_related('assigned_group').all()
	technician_groups = TechnicianGroup.objects.all()
	catalog_items = ServiceCatalogItem.objects.select_related('category').all().order_by('order', 'id')

	fields_schema = []
	for f in fields:
		fields_schema.append({
			'id': f.id,
			'key': f.field_key,
			'label': f.label,
			'type': f.field_type,
			'type_display': f.get_field_type_display(),
			'category_id': f.category_id if f.category_id else 'global',
			'category_name': f.category.name if f.category else 'Global',
			'condition_type': f.condition_type,
			'condition_type_display': f.get_condition_type_display(),
			'condition_field_key': f.condition_field_key,
			'condition_operator': f.condition_operator,
			'condition_value': f.condition_value,
			'options': f.options,
			'required': f.required,
			'order': f.order,
			'is_active': f.is_active,
			'help_text': f.help_text,
			'max_file_size_mb': f.max_file_size_mb,
		})

	
	return render(request, 'tickets/form_builder.html', {
		'form': form,
		'fields': fields,
		'fields_schema_json': json.dumps(fields_schema),
		'categories': categories,
		'technician_groups': technician_groups,
		'catalog_items': catalog_items,
	})


@login_required(login_url='accounts:login')
@require_http_methods(['GET', 'POST'])
def service_catalog_manager(request):
	if request.user.profile.role != UserRole.ADMIN or not request.user.is_staff:
		return redirect('accounts:dashboard')

	if request.method == 'POST':
		action = request.POST.get('action')
		if action == 'edit':
			item_id = request.POST.get('item_id')
			item = get_object_or_404(ServiceCatalogItem, pk=item_id)
			form = ServiceCatalogItemForm(request.POST, instance=item)
			if form.is_valid():
				form.save()
				messages.success(request, f"Service catalog item '{item.title}' updated successfully.")
				return redirect('tickets:catalog_manager')
			else:
				errs = '; '.join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
				messages.error(request, f"Failed to update service catalog item: {errs}")
		elif action == 'delete':
			item_id = request.POST.get('item_id')
			item = get_object_or_404(ServiceCatalogItem, pk=item_id)
			title = item.title
			item.delete()
			messages.success(request, f"Catalog item '{title}' deleted.")
			return redirect('tickets:catalog_manager')
		else:
			form = ServiceCatalogItemForm(request.POST)
			if form.is_valid():
				item = form.save()
				messages.success(request, f"Service catalog item '{item.title}' published successfully.")
				return redirect('tickets:catalog_manager')
			else:
				errs = '; '.join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
				messages.error(request, f"Please correct errors in form: {errs}")

	form = ServiceCatalogItemForm()
	catalog_items = ServiceCatalogItem.objects.select_related('category').order_by('order', 'id')
	categories = Category.objects.all()
	return render(request, 'tickets/service_catalog.html', {
		'form': form,
		'catalog_items': catalog_items,
		'categories': categories,
	})


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def service_catalog_toggle(request, pk):
	if request.user.profile.role != UserRole.ADMIN or not request.user.is_staff:
		return redirect('accounts:dashboard')
	item = get_object_or_404(ServiceCatalogItem, pk=pk)
	action = request.POST.get('action')
	if action == 'toggle_homepage':
		item.show_on_homepage = not item.show_on_homepage
		item.save()
		state = "visible on" if item.show_on_homepage else "hidden from"
		messages.success(request, f"'{item.title}' is now {state} the user homepage.")
	elif action == 'delete':
		item.delete()
		messages.success(request, f"Catalog item '{item.title}' deleted.")
	return redirect('tickets:catalog_manager')



@login_required(login_url='accounts:login')
@require_http_methods(['GET', 'POST'])
def issue_form_field_edit(request, pk):
	if request.user.profile.role != UserRole.ADMIN or not request.user.is_staff:
		return redirect('accounts:dashboard')
	field = get_object_or_404(IssueFormField, pk=pk)
	form = IssueFormFieldForm(request.POST or None, instance=field)
	if request.method == 'POST' and form.is_valid():
		saved_field = form.save()
		if saved_field.options:
			for opt in saved_field.options:
				if opt.strip() and opt.strip().lower() != 'other':
					Category.objects.get_or_create(
						name=opt.strip(),
						defaults={'description': f'Auto-created category from {saved_field.label}'}
					)
		messages.success(request, f"Form field '{saved_field.label}' updated successfully.")
		return redirect('tickets:form_builder')

	all_fields = IssueFormField.objects.exclude(pk=field.pk).filter(is_active=True).order_by('order', 'id')
	return render(request, 'tickets/form_field_edit.html', {
		'form': form,
		'field': field,
		'all_fields': all_fields,
	})



@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def issue_form_field_delete(request, pk):
	if request.user.profile.role != UserRole.ADMIN or not request.user.is_staff:
		return redirect('accounts:dashboard')
	field = get_object_or_404(IssueFormField, pk=pk)
	label = field.label
	field.delete()
	messages.success(request, f"Form field '{label}' removed from form.")
	return redirect('tickets:form_builder')



@login_required(login_url='accounts:login')
def my_tickets(request):
	status_filter = request.GET.get('status', '')
	all_tickets = Ticket.objects.filter(reporter=request.user).select_related('category', 'assigned_technician', 'assigned_group').order_by('-created_at')
	
	for t in all_tickets:
		t.check_sla_breach()
	
	filtered_tickets = all_tickets
	if status_filter in dict(TicketStatus.choices):
		filtered_tickets = filtered_tickets.filter(status=status_filter)

	context = {
		'tickets': filtered_tickets,
		'total_count': all_tickets.count(),
		'open_count': all_tickets.filter(status=TicketStatus.OPEN).count(),
		'in_progress_count': all_tickets.filter(status=TicketStatus.IN_PROGRESS).count(),
		'resolved_count': all_tickets.filter(status__in=[TicketStatus.RESOLVED, TicketStatus.CLOSED]).count(),
		'selected_status': status_filter,
		'status_choices': TicketStatus.choices,
	}
	return render(request, 'tickets/my_tickets.html', context)


@login_required(login_url='accounts:login')
def user_service_catalog(request):
	catalog_items = ServiceCatalogItem.objects.filter(is_active=True, show_on_homepage=True).select_related('category').order_by('order', 'id')
	return render(request, 'tickets/user_service_catalog.html', {
		'catalog_items': catalog_items,
	})



@login_required(login_url='accounts:login')
@require_http_methods(['GET', 'POST'])
def ticket_edit(request, pk):
	# Ticket records are immutable for audit integrity. Redirect to ticket detail.
	ticket = get_object_or_404(Ticket, pk=pk)
	messages.info(request, "Ticket content is locked for audit integrity. You can manage status, assignments, and notes here.")
	return redirect('tickets:detail', pk=ticket.pk)


@login_required(login_url='accounts:login')
def ticket_detail(request, pk):
	ticket = get_object_or_404(
		Ticket.objects.select_related('reporter', 'assigned_technician', 'category', 'assigned_group'),
		pk=pk
	)
	
	is_reporter = (ticket.reporter == request.user)
	is_technician = (ticket.assigned_technician == request.user)
	is_admin = (request.user.is_staff or (hasattr(request.user, 'profile') and request.user.profile.role == UserRole.ADMIN))

	if not (is_reporter or is_technician or is_admin):
		messages.error(request, "You do not have permission to view this ticket.")
		return redirect('accounts:dashboard')

	ticket.check_sla_breach()

	# Mark unread notifications for this ticket and user as read
	from .models import TicketNotification
	TicketNotification.objects.filter(ticket=ticket, recipient=request.user, is_read=False).update(is_read=True)

	# 5-Stage Visual Progress Pipeline
	step_submitted = True
	step_assigned = bool(ticket.assigned_technician or ticket.assigned_group)
	step_in_progress = (ticket.status in [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED])
	step_resolved = (ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED])
	step_closed = (ticket.status == TicketStatus.CLOSED)

	# Available status choices: Technicians CANNOT directly mark as Closed (Client confirmation required)
	if is_admin:
		status_choices = TicketStatus.choices
	elif is_technician:
		status_choices = [
			(TicketStatus.IN_PROGRESS, 'In Progress'),
			(TicketStatus.RESOLVED, 'Resolved (Submit for Client Confirmation)'),
		]
		if ticket.status == TicketStatus.OPEN:
			status_choices.insert(0, (TicketStatus.OPEN, 'Open'))
	else:
		status_choices = []

	awaiting_client_confirmation = (ticket.status == TicketStatus.RESOLVED and is_reporter)
	latest_resolution_comment = ticket.comments.filter(content__icontains='Resolved').order_by('-created_at').first()

	context = {
		'ticket': ticket,
		'comments': ticket.comments.select_related('author').order_by('created_at'),
		'history': ticket.history.select_related('changed_by').order_by('-changed_at'),
		'status_choices': status_choices,
		'can_update_status': (is_technician or is_admin) and (ticket.status != TicketStatus.CLOSED or is_admin),
		'is_reporter': is_reporter,
		'is_technician': is_technician,
		'is_admin': is_admin,
		'awaiting_client_confirmation': awaiting_client_confirmation,
		'latest_resolution_comment': latest_resolution_comment,
		'step_submitted': step_submitted,
		'step_assigned': step_assigned,
		'step_in_progress': step_in_progress,
		'step_resolved': step_resolved,
		'step_closed': step_closed,
	}
	return render(request, 'tickets/ticket_detail.html', context)



@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def ticket_update_status(request, pk):
	ticket = get_object_or_404(Ticket, pk=pk)
	is_technician = (ticket.assigned_technician == request.user)
	is_admin = (request.user.is_staff or (hasattr(request.user, 'profile') and request.user.profile.role == UserRole.ADMIN))

	if not (is_technician or is_admin):
		messages.error(request, "You do not have permission to update this ticket's status.")
		return redirect('accounts:dashboard')

	new_status = request.POST.get('status')
	comment_text = request.POST.get('comment', '').strip()
	valid_statuses = dict(TicketStatus.choices)

	# Enforce rule: Technicians cannot directly close tickets without client confirmation
	if not is_admin and new_status == TicketStatus.CLOSED:
		messages.error(request, "Technicians cannot mark tickets directly as Closed. Mark as 'Resolved' so the client who reported the issue can verify and confirm closure.")
		return redirect('tickets:detail', pk=ticket.pk)

	from .models import TicketNotification

	if new_status in valid_statuses and new_status != ticket.status:
		old_display = ticket.get_status_display()
		new_display = valid_statuses[new_status]

		ticket.status = new_status
		if new_status == TicketStatus.RESOLVED and not ticket.resolved_at:
			ticket.resolved_at = timezone.now()
		ticket.save()

		TicketHistory.objects.create(
			ticket=ticket,
			changed_by=request.user,
			field_name='status',
			old_value=old_display,
			new_value=new_display,
		)

		# If technician marked as Resolved, notify reporter to confirm
		if new_status == TicketStatus.RESOLVED:
			TicketNotification.objects.create(
				recipient=ticket.reporter,
				ticket=ticket,
				title=f"Ticket #{ticket.ticket_number} Marked as Resolved",
				message=f"Technician {request.user.get_full_name() or request.user.username} has resolved your ticket '{ticket.title}'. Please verify the fix and confirm closure.",
				notification_type=TicketNotification.NotificationType.RESOLVED
			)
			try:
				from .services import send_ticket_resolved_email
				send_ticket_resolved_email(ticket, resolution_notes=comment_text)
			except Exception as e:
				import logging
				logging.getLogger(__name__).error(f"Failed to dispatch resolution email: {e}")
			messages.success(request, f"Ticket #{ticket.ticket_number} marked as Resolved. The client ({ticket.reporter.username}) has been notified via email and dashboard to verify and confirm closure.")
		else:
			if ticket.reporter != request.user:
				TicketNotification.objects.create(
					recipient=ticket.reporter,
					ticket=ticket,
					title=f"Ticket #{ticket.ticket_number} Status Updated",
					message=f"Ticket status changed to {new_display}.",
					notification_type=TicketNotification.NotificationType.COMMENT
				)
			messages.success(request, f"Ticket #{ticket.ticket_number} status updated to {new_display}.")

	if comment_text or request.FILES.get('attachment'):
		attachment = request.FILES.get('attachment')
		TicketComment.objects.create(
			ticket=ticket,
			author=request.user,
			content=comment_text or f"Status updated to {ticket.get_status_display()}.",
			attachment=attachment
		)
		if not new_status or new_status == ticket.status:
			messages.success(request, "Status note added successfully.")

	return redirect(f"/tickets/{ticket.pk}/#status")



@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def ticket_confirm_resolution(request, pk):
	"""Normal user confirmation to either Close the resolved ticket or Reopen it with feedback"""
	ticket = get_object_or_404(Ticket, pk=pk)
	is_reporter = (ticket.reporter == request.user)
	is_admin = (request.user.is_staff or (hasattr(request.user, 'profile') and request.user.profile.role == UserRole.ADMIN))

	if not (is_reporter or is_admin):
		messages.error(request, "Only the user who reported this ticket (or an admin) can confirm its resolution.")
		return redirect('tickets:detail', pk=ticket.pk)

	action = request.POST.get('action')
	from .models import TicketNotification

	if action == 'confirm_close':
		old_display = ticket.get_status_display()
		ticket.status = TicketStatus.CLOSED
		ticket.save()

		TicketHistory.objects.create(
			ticket=ticket,
			changed_by=request.user,
			field_name='status',
			old_value=old_display,
			new_value=TicketStatus.CLOSED.label,
		)

		feedback = request.POST.get('closing_notes', '').strip()
		comment_body = f"✔ Resolution confirmed by client ({request.user.username}). Ticket closed."
		if feedback:
			comment_body += f"\nClient Feedback: {feedback}"

		TicketComment.objects.create(
			ticket=ticket,
			author=request.user,
			content=comment_body
		)

		if ticket.assigned_technician:
			TicketNotification.objects.create(
				recipient=ticket.assigned_technician,
				ticket=ticket,
				title=f"Ticket #{ticket.ticket_number} Confirmed & Closed",
				message=f"Client {request.user.username} has verified the fix and confirmed closure of Ticket #{ticket.ticket_number}.",
				notification_type=TicketNotification.NotificationType.CLOSED
			)

		messages.success(request, f"Thank you! You have confirmed the resolution and closed Ticket #{ticket.ticket_number}.")

	elif action == 'reopen':
		reopen_reason = request.POST.get('reopen_reason', '').strip()
		if not reopen_reason:
			messages.error(request, "Please provide an explanation describing why the issue is not yet resolved.")
			return redirect('tickets:detail', pk=ticket.pk)

		old_display = ticket.get_status_display()
		ticket.status = TicketStatus.IN_PROGRESS
		ticket.save()

		TicketHistory.objects.create(
			ticket=ticket,
			changed_by=request.user,
			field_name='status',
			old_value=old_display,
			new_value=f"{TicketStatus.IN_PROGRESS.label} (Reopened by client)",
		)

		attachment = request.FILES.get('reopen_attachment')
		TicketComment.objects.create(
			ticket=ticket,
			author=request.user,
			content=f"↺ ISSUE REOPENED BY CLIENT ({request.user.username}):\n{reopen_reason}",
			attachment=attachment
		)

		if ticket.assigned_technician:
			TicketNotification.objects.create(
				recipient=ticket.assigned_technician,
				ticket=ticket,
				title=f"Ticket #{ticket.ticket_number} Reopened by Client",
				message=f"Client {request.user.username} reported that the problem is not resolved: \"{reopen_reason}\"",
				notification_type=TicketNotification.NotificationType.REOPENED
			)

		messages.warning(request, f"Ticket #{ticket.ticket_number} has been reopened. Technician {ticket.assigned_technician.username if ticket.assigned_technician else 'Support Team'} has been alerted.")

	return redirect('tickets:detail', pk=ticket.pk)



@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def ticket_add_comment(request, pk):
	ticket = get_object_or_404(Ticket, pk=pk)
	is_reporter = (ticket.reporter == request.user)
	is_technician = (ticket.assigned_technician == request.user)
	is_admin = (request.user.is_staff or (hasattr(request.user, 'profile') and request.user.profile.role == UserRole.ADMIN))

	if not (is_reporter or is_technician or is_admin):
		messages.error(request, "You do not have permission to comment on this ticket.")
		return redirect('accounts:dashboard')

	content = request.POST.get('content', '').strip()
	attachment = request.FILES.get('attachment')

	if content or attachment:
		TicketComment.objects.create(
			ticket=ticket,
			author=request.user,
			content=content,
			attachment=attachment
		)

		# Notify other party
		from .models import TicketNotification
		recipient = None
		if is_reporter and ticket.assigned_technician:
			recipient = ticket.assigned_technician
		elif not is_reporter:
			recipient = ticket.reporter

		if recipient and recipient != request.user:
			TicketNotification.objects.create(
				recipient=recipient,
				ticket=ticket,
				title=f"New Message on Ticket #{ticket.ticket_number}",
				message=f"{request.user.username}: {content[:120]}{'...' if len(content) > 120 else ''}",
				notification_type=TicketNotification.NotificationType.COMMENT
			)

		messages.success(request, "Message posted successfully.")
	else:
		messages.error(request, "Message content cannot be empty.")

	return redirect(f"/tickets/{ticket.pk}/#activity")


@login_required(login_url='accounts:login')
def notification_mark_read(request, pk):
	from .models import TicketNotification
	notif = get_object_or_404(TicketNotification, pk=pk, recipient=request.user)
	notif.is_read = True
	notif.save()
	if notif.ticket:
		return redirect('tickets:detail', pk=notif.ticket.pk)
	return redirect('accounts:dashboard')


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def notifications_clear_all(request):
	from .models import TicketNotification
	TicketNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
	messages.success(request, "All notifications marked as read.")
	return redirect(request.META.get('HTTP_REFERER') or 'accounts:dashboard')


