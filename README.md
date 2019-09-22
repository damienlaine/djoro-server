# Djoro server 

## Production environment

### Launch the server for the beta test

	(virt) python manage_beta.py runserver 0.0.0.0:9000

## Development environment

### Setup virtualenv
I strongly recommend using virtualenv to create customized python environment for development.
Tutorial here: http://simononsoftware.com/virtualenv-tutorial/

### Install python dependencies 

    (virt)-> pip install -r requirements.txt

### First local install
	
Create the database:

	 (virt)-> python manage.py makemigrations
	 (virt)-> python manage.py migrate
	 
Create a super user:

	(virt)-> python manage.py createsuperuser
	
Start the server:

	(virt)-> python manage.py runserver 0.0.0.0:8000

**Caution:** if you use localhost:8000 to request the server, you could have CSRF errors (cross site validation). To avoid this, request the server on its IP address instead of localhost.
When you make requests on thermlabs.com server with postman, you have to be logged in order to avoid CSRF errors.

## Development guidelines

### Logging

One logger by django application named `djoro.__application_name__`. For example, use the folllowing code in a the thermostats application : 

	```
	import logging
	logger = logging.getLogger('djoro.thermostats')
	
	...
	
	def whatever():
		logger.debug('log whatever message')
	```