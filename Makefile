serve:
	python manage.py runserver 0.0.0.0:8000

init:
	django-admin compilemessages
	python manage.py migrate
	python manage.py createsuperuser --username admin 
	python manage.py makemigrations main
	python manage.py migrate
	python manage.py genrestaurants 5
	python manage.py genusers 20
	python manage.py genorders 60
	python manage.py genreviews 40

clean:
	rm -f db.sqlite3
	rm -rf main/migrations
	rm -rf images


