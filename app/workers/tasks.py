from app.workers.celery_app import celery_app

@celery_app.task

def send_test_email(email:str):
    print(f"Sending email to {email}")
    return f"Email sent to {email}"

