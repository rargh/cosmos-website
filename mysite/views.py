from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.template.loader import get_template
from django.shortcuts import render_to_response
from django.template import RequestContext
import requests


from mysite.settings_pr import EMAIL_HOST_USER, DEFAULT_FROM_EMAIL


def set_values(object, values, fields):
	for field in fields:
		setattr(object, field, values[field])
	return object

# TODO: Proper django form
def update_profile(request):
	if request.method == 'POST':
		if request.user.is_authenticated():
			email = request.POST['email']
			if request.user.email != email and User.objects.filter(username=email).exists():
				return redirect('/profile?updated=false&error=email-exists')

			user = User.objects.get(id=int(request.user.id))

			fields = ['first_name', 'last_name', 'email']
			user = set_values(user, request.POST, fields)
			user.username = email

			fields = ['department', 'program', 'nationality', 'tue_id', 'phone_nr', 'gender', 'card_number']
			user.profile = set_values(user.profile, request.POST, fields)

			user.save()
			return redirect('/profile?updated=true')
	return redirect('/login')

def create_member(request):
	if request.method == 'POST':
		email = request.POST['email']
		if User.objects.filter(username=email).exists():
			return redirect('/join?joined=false&error=email-exists')
		if request.POST['password'] != request.POST['password-confirm']:
			return redirect('/join?joined=false&error=password')

		user = User.objects.create_user(email)

		fields = ['first_name', 'last_name']
		user = set_values(user, request.POST, fields)
		user.email = email

		fields = ['department', 'program', 'nationality', 'tue_id', 'phone_nr', 'gender', 'card_number']
		user.profile = set_values(user.profile, request.POST, fields)

		user.password = make_password(request.POST['password'])
		user.profile.key_access = 'No'
		user.profile.member_type = 'Pending'

		user.save()

		message = "Dear " + user.first_name + ", \n \n Your account has been created successfully, your information " \
											  "will be validated as soon as possible by our board members. As soon as " \
											  "your information is verified, you will receive an e-mail from us. \n \n " \

		# Email the user that just signed up
		send_mail(
			'Signup Confirmation',
			message,
			DEFAULT_FROM_EMAIL,
			[user.email],
			# fail_silently=False,
		)

		message = "Someone just signed up, please go to www.cosmostue.nl/requests to review his request."

		# Email internal affairs to let them know someone signed up
		send_mail(
			'Someone just signed up',
			message,
			DEFAULT_FROM_EMAIL,
			['internal.cosmos@tue.nl'],
		)

		return redirect('/join?joined=true')

def list_requests(request):
	if request.user.is_authenticated and request.user.is_staff:

		join_requests = User.objects.filter(profile__member_type='Pending')
		request_context = RequestContext(request, {"requests": join_requests})

		return render_to_response('request-list.html', request_context)
	return redirect('/login')

def accept_request(request):
	if request.user.is_authenticated and request.user.is_staff:

		id = request.GET.get('id')
		if id is None:
			return redirect('/requests')
		try:
			user = User.objects.get(id=id)
		except User.DoesNotExist:
			return redirect('/requests')

		user.profile.member_type = 'MEMBER'
		user.save()

		message = "Dear " + user.first_name + ", \n \n Your information has been verified and your account is now " \
											  "activated. \n \n Best regards, \n The Cosmos Website Committee \n " \

		# Email the user that just got accepted
		send_mail(
			'Your account has been verified',
			message,
			DEFAULT_FROM_EMAIL,
			[user.email],
		)

		return redirect('/requests')
	return redirect('/login')

# For now it just makes the user's member_type "rejected". Will consider deleting from DB
def reject_request(request):
	if request.user.is_authenticated and request.user.is_staff:

		id = request.GET.get('id')
		if id is None:
			return redirect('/requests')
		try:
			user = User.objects.get(id=id)
		except User.DoesNotExist:
			return redirect('/requests')

		user.profile.member_type = 'Rejected'
		user.save()

		message = "Dear " + user.first_name + ", \n \n We regret to inform you that after reviewing your information, " \
											  "your membership request has been rejected. If you would like to reach us, " \
											  "you can do so sending an email to cosmos@tue.nl. \n \n " \
											  "Best regards, \n The Cosmos Website Committee \n " \

		# Email the user that just got rejected
		send_mail(
			'Your account has been verified',
			message,
			DEFAULT_FROM_EMAIL,
			[user.email],
		)

		return redirect('/requests')
	return redirect('/login')

# Retrieves images from facebook album. If album does not exist, the user is redirected to the albums page (/association/photos/)
def display_album(request):
	album_id = request.get_full_path().split("/")[-2] #Get album id. Url ends with /, so we split by '/' and get the second to last.
	# TODO: SET TOKEN IN SETTINGS
	TOKEN = "EAAKJjBrYxBoBAFhEcUT0KZBUfAYZAfVYxLCveRLc8JSmkywdBTPvBR3c5eiL6sj2e8SgPZBaAEVAcvw4Tk1UvsxNhQD06Q8iEH9JBSWNH5LkCZB09n81t3lT7mgZBm16MyslWErJEsytCLgZAL2HtxNwZAU6BmHXvJX0qrzu8JomW92YLf2UPbO"
	API_VERSION = "v3.1"

	r = requests.get('https://graph.facebook.com/%s/%s/?fields=photos.limit(1000){images},description,name&access_token=%s' % (API_VERSION, album_id, TOKEN))
	if r.status_code != requests.codes.ok:
		return redirect('/association/photos/')

	template = get_template("/widgets/gallery_album.html")
	context = RequestContext(request, {'album': r.json()})
	html = template.render(context)

	return HttpResponse(html)

