from celery import Celery
import dns.resolver
import os
from datetime import datetime

celery = Celery('tasks', broker='redis://localhost:6379/0')

def check_mx_record(email):
    try:
        domain = email.split('@')[-1]
        return bool(dns.resolver.resolve(domain, 'MX'))
    except:
        return False

@celery.task(bind=True)
def validate_emails_task(self, filepath):
    valid_emails = []
    invalid_emails = []
    
    # Count total lines first for progress
    with open(filepath, 'r') as f:
        total_lines = sum(1 for _ in f)
    
    # Process emails
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            email = line.strip()
            if email:  # Skip empty lines
                if check_mx_record(email):
                    valid_emails.append(email)
                else:
                    invalid_emails.append(email)
            
            # Update progress every 10 emails
            if i % 10 == 0:
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i + 1,
                        'total': total_lines,
                        'percent': int((i + 1) / total_lines * 100)
                    }
                )
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(filepath).replace('.txt', '')
    
    valid_path = f"valid_{base_name}_{timestamp}.txt"
    invalid_path = f"invalid_{base_name}_{timestamp}.txt"
    
    with open(os.path.join('results', valid_path), 'w') as f:
        f.write("\n".join(valid_emails))
    
    with open(os.path.join('results', invalid_path), 'w') as f:
        f.write("\n".join(invalid_emails))
    
    return {
        'valid': valid_path,
        'invalid': invalid_path,
        'valid_count': len(valid_emails),
        'invalid_count': len(invalid_emails),
        'percent': 100
    }
